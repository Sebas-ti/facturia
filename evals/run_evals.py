#!/usr/bin/env python3
"""Full-pipeline evals (docs/spec.md §9): runs the complete LangGraph graph
(app.graph.build_graph) over the sample invoices (F01 -> F15 by default, in
order — F09 is only a duplicate once F01 has already been processed and
persisted) and compares extraction, findings and decision against
data/ground_truth.json.

`--mock` never calls Azure and never lets the real PDF content reach the
extraction result (that comes from evals/fixtures.py's synthetic, ground-
truth-derived fixture) — AGENTS.md rule 6. It does read the real bytes from
data/facturas/ now, because `ingest`'s is_scanned detection (app.services.pdf)
needs a structurally valid PDF to parse; that's a free, local, read-only
operation, not the kind of Azure call or content dependency rule 6 is about.
`--live` calls the real Azure Document Intelligence + OpenAI clients too,
which costs money, so use `--ids` to limit the run (e.g. `--ids F01,F15`)
instead of burning through all 15 invoices by default. Both modes use the
real local Postgres and Azurite — those aren't paid Azure services, and the
pipeline needs a real DB to match/reconcile against.
"""

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Invoice, Supplier
from app.db.session import SessionLocal
from app.graph import GraphState, build_graph
from app.schemas.finding import FindingCode
from app.schemas.invoice import ExtractedInvoice, InvoiceLine
from app.services.blob import BlobStorageClient
from app.services.doc_intelligence import (
    AzureDocumentIntelligenceClient,
    DocumentIntelligenceClient,
    FixtureDocumentIntelligenceClient,
)
from app.services.explain import (
    AzureDecisionExplainerClient,
    DecisionExplainerClient,
    MockDecisionExplainerClient,
)
from app.services.llm import AzureInvoiceLLMClient, InvoiceLLMClient, MockInvoiceLLMClient
from scripts.seed import seed

REPO_ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH_PATH = REPO_ROOT / "data" / "ground_truth.json"
FACTURAS_DIR = REPO_ROOT / "data" / "facturas"
REPORTS_DIR = Path(__file__).resolve().parent / "reports"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from expected import expected_invoice
from fixtures import build_raw_extraction

INVOICE_FIELDS = (
    "supplier_nit",
    "supplier_dv",
    "supplier_name",
    "invoice_number",
    "issue_date",
    "due_date",
    "purchase_order",
    "subtotal",
    "vat_total",
    "total",
    "cufe",
    "bank_account",
)
LINE_FIELDS = ("sku", "description", "quantity", "unit_price", "vat_rate", "line_subtotal")
DECISIONS = ("APROBAR", "REVISION", "RECHAZAR")


@dataclass
class FieldTally:
    matches: int = 0
    total: int = 0

    def record(self, is_match: bool) -> None:
        self.total += 1
        self.matches += int(is_match)

    @property
    def precision(self) -> float:
        return self.matches / self.total if self.total else 0.0


@dataclass
class FindingTally:
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    def record(self, *, expected: bool, actual: bool) -> None:
        self.true_positives += int(expected and actual)
        self.false_positives += int(actual and not expected)
        self.false_negatives += int(expected and not actual)

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom else 1.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom else 1.0


@dataclass
class DecisionTally:
    confusion: dict[tuple[str, str], int] = field(default_factory=dict)
    correct: int = 0
    total: int = 0

    def record(self, expected: str, actual: str | None) -> None:
        actual = actual or "NINGUNA"
        self.total += 1
        self.correct += int(expected == actual)
        key = (expected, actual)
        self.confusion[key] = self.confusion.get(key, 0) + 1

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


@dataclass
class InvoiceResult:
    factura_id: str
    all_fields_match: bool
    error: str | None = None
    mismatches: list[str] = field(default_factory=list)


def _compare_lines(
    actual: list[InvoiceLine], expected: list[InvoiceLine], tallies: dict[str, FieldTally]
) -> list[str]:
    mismatches = []
    if len(actual) != len(expected):
        mismatches.append(f"line count {len(actual)} != {len(expected)}")
        for field_name in LINE_FIELDS:
            for _ in range(max(len(actual), len(expected))):
                tallies[field_name].record(False)
        return mismatches

    for i, (actual_line, expected_line) in enumerate(zip(actual, expected, strict=True)):
        for field_name in LINE_FIELDS:
            actual_value = getattr(actual_line, field_name)
            expected_value = getattr(expected_line, field_name)
            is_match = actual_value == expected_value
            tallies[field_name].record(is_match)
            if not is_match:
                mismatches.append(f"line[{i}].{field_name}: {actual_value!r} != {expected_value!r}")
    return mismatches


def _persist_invoice(
    db: Session, invoice_id: UUID, extracted: ExtractedInvoice | None, result: dict[str, Any]
) -> None:
    """Writes the processed invoice so later facturas in the run (F09's
    duplicate-of-F01 check, quantity accumulation) see it, the same way a
    real caller would persist each invoice as it's processed."""
    supplier_id = None
    if extracted is not None:
        supplier_id = db.scalars(
            select(Supplier.id).where(Supplier.nit == extracted.supplier_nit)
        ).first()

    db.add(
        Invoice(
            id=invoice_id,
            file_hash=result["file_hash"],
            blob_url=result["blob_url"],
            status="PROCESSED",
            decision=result["decision"],
            supplier_id=supplier_id,
            invoice_number=extracted.invoice_number if extracted else "UNKNOWN",
            total=extracted.total if extracted else Decimal(0),
            extracted=extracted.model_dump(mode="json") if extracted else None,
        )
    )
    db.commit()


def run(
    db: Session, facturas: list[dict[str, Any]], *, live: bool
) -> tuple[dict[str, FieldTally], dict[str, FindingTally], DecisionTally, list[InvoiceResult]]:
    db.execute(delete(Invoice))  # clean slate: duplicate detection must see only this run
    db.commit()

    field_tallies: dict[str, FieldTally] = {
        name: FieldTally() for name in (*INVOICE_FIELDS, *LINE_FIELDS)
    }
    finding_tallies: dict[str, FindingTally] = {code.value: FindingTally() for code in FindingCode}
    decision_tally = DecisionTally()
    results: list[InvoiceResult] = []

    llm_client: InvoiceLLMClient = AzureInvoiceLLMClient() if live else MockInvoiceLLMClient()
    explainer: DecisionExplainerClient = (
        AzureDecisionExplainerClient() if live else MockDecisionExplainerClient()
    )
    live_doc_client = AzureDocumentIntelligenceClient() if live else None
    blob_client = BlobStorageClient()

    for factura in facturas:
        expected = expected_invoice(factura)
        expected_codes = set(factura["hallazgos_esperados"])
        expected_decision: str = factura["decision_esperada"]

        # Real bytes in both modes: ingest's is_scanned detection needs a
        # structurally valid PDF. --mock still never calls Azure or lets this
        # content reach the extraction result — that comes from the fixture.
        pdf_bytes = (FACTURAS_DIR / factura["archivo"]).read_bytes()

        doc_client: DocumentIntelligenceClient
        if live:
            assert live_doc_client is not None
            doc_client = live_doc_client
        else:
            file_hash = hashlib.sha256(pdf_bytes).hexdigest()
            doc_client = FixtureDocumentIntelligenceClient(
                {file_hash: build_raw_extraction(factura)}
            )

        invoice_id = uuid4()
        graph = build_graph(
            db=db,
            doc_intelligence=doc_client,
            llm=llm_client,
            blob=blob_client,
            explainer=explainer,
        )
        initial_state: GraphState = {
            "invoice_id": invoice_id,
            "file_hash": "",
            "is_scanned": False,
            "extracted": None,
            "field_confidence": {},
            "findings": [],
            "decision": None,
            "explanation": None,
            "supplier_email_draft": None,
            "pdf_bytes": pdf_bytes,
            "blob_url": "",
        }

        try:
            result = graph.invoke(initial_state)
        except (ValueError, KeyError) as exc:
            for name in INVOICE_FIELDS:
                field_tallies[name].record(False)
            for name in LINE_FIELDS:
                for _ in expected.lines:
                    field_tallies[name].record(False)
            results.append(InvoiceResult(factura["id"], all_fields_match=False, error=str(exc)))
            continue

        actual = result["extracted"]
        mismatches = []
        if actual is None:
            mismatches.append("extracted is None")
            for name in INVOICE_FIELDS:
                field_tallies[name].record(False)
        else:
            for field_name in INVOICE_FIELDS:
                actual_value = getattr(actual, field_name)
                expected_value = getattr(expected, field_name)
                is_match = actual_value == expected_value
                field_tallies[field_name].record(is_match)
                if not is_match:
                    mismatches.append(f"{field_name}: {actual_value!r} != {expected_value!r}")
            mismatches += _compare_lines(actual.lines, expected.lines, field_tallies)

        actual_codes = {f.code.value for f in result["findings"]}
        for code in expected_codes | actual_codes:
            finding_tallies[code].record(expected=code in expected_codes, actual=code in actual_codes)
        if actual_codes != expected_codes:
            mismatches.append(f"hallazgos: {sorted(actual_codes)} != {sorted(expected_codes)}")

        actual_decision = result["decision"]
        decision_tally.record(expected_decision, actual_decision)
        if actual_decision != expected_decision:
            mismatches.append(f"decisión: {actual_decision!r} != {expected_decision!r}")

        _persist_invoice(db, invoice_id, actual, result)

        results.append(
            InvoiceResult(factura["id"], all_fields_match=not mismatches, mismatches=mismatches)
        )

    return field_tallies, finding_tallies, decision_tally, results


def render_report(
    field_tallies: dict[str, FieldTally],
    finding_tallies: dict[str, FindingTally],
    decision_tally: DecisionTally,
    results: list[InvoiceResult],
    *,
    live: bool,
) -> str:
    mode_note = (
        "Modo `--live`: Azure Document Intelligence + Azure OpenAI reales (Postgres/Azurite "
        "locales en ambos modos)."
        if live
        else "Modo `--mock`, sin llamadas a Azure (Postgres/Azurite locales)."
    )
    lines = [
        "# Evals del pipeline completo",
        "",
        f"Generado: {datetime.now(UTC).isoformat(timespec='seconds')}",
        "",
        f"Grafo completo (docs/spec.md §9): extracción, hallazgos y decisión. {mode_note}",
        "",
        "## Extracción: precisión por campo",
        "",
        "| Campo | Precisión | Aciertos/Total |",
        "|---|---|---|",
    ]
    for name, tally in field_tallies.items():
        lines.append(f"| `{name}` | {tally.precision:.0%} | {tally.matches}/{tally.total} |")

    lines += [
        "",
        "## Hallazgos: precisión y recall por código",
        "",
        "| Código | Precisión | Recall | TP | FP | FN |",
        "|---|---|---|---|---|---|",
    ]
    for code, tally in finding_tallies.items():
        if tally.true_positives == tally.false_positives == tally.false_negatives == 0:
            continue  # never expected nor produced in this run — not worth a row
        lines.append(
            f"| `{code}` | {tally.precision:.0%} | {tally.recall:.0%} | "
            f"{tally.true_positives} | {tally.false_positives} | {tally.false_negatives} |"
        )

    lines += [
        "",
        (
            f"## Decisión: accuracy y matriz de confusión ({decision_tally.accuracy:.0%}, "
            f"{decision_tally.correct}/{decision_tally.total})"
        ),
        "",
        "| Esperada \\ Obtenida | " + " | ".join(DECISIONS) + " |",
        "|---|" + "---|" * len(DECISIONS),
    ]
    for expected_decision in DECISIONS:
        row = [str(decision_tally.confusion.get((expected_decision, d), 0)) for d in DECISIONS]
        lines.append(f"| {expected_decision} | " + " | ".join(row) + " |")

    passed = sum(1 for r in results if r.all_fields_match)
    lines += [
        "",
        f"## Resultado por factura ({passed}/{len(results)} sin diferencias)",
        "",
        "| Factura | OK | Detalle |",
        "|---|---|---|",
    ]
    for r in results:
        detail = r.error or ("; ".join(r.mismatches) if r.mismatches else "")
        lines.append(f"| {r.factura_id} | {'OK' if r.all_fields_match else 'FALLA'} | {detail} |")

    return "\n".join(lines) + "\n"


def build_report_data(
    field_tallies: dict[str, FieldTally],
    finding_tallies: dict[str, FindingTally],
    decision_tally: DecisionTally,
    results: list[InvoiceResult],
    *,
    live: bool,
) -> dict[str, Any]:
    """Structured twin of `render_report`'s Markdown, written as JSON so the
    API (`app/services/eval_parser.py`) reads real data instead of
    regex-parsing prose — AGENTS.md rule 2 in spirit: don't parse free text
    for something a page depends on."""
    mode_note = (
        "Modo `--live`: Azure Document Intelligence + Azure OpenAI reales (Postgres/Azurite "
        "locales en ambos modos)."
        if live
        else "Modo `--mock`, sin llamadas a Azure (Postgres/Azurite locales)."
    )

    extraction_accuracy = [
        {
            "field": name,
            "precision_pct": round(tally.precision * 100, 1),
            "hits": tally.matches,
            "total": tally.total,
        }
        for name, tally in field_tallies.items()
    ]

    findings_accuracy = [
        {
            "code": code,
            "precision_pct": round(tally.precision * 100, 1),
            "recall_pct": round(tally.recall * 100, 1),
            "tp": tally.true_positives,
            "fp": tally.false_positives,
            "fn": tally.false_negatives,
        }
        for code, tally in finding_tallies.items()
        if not (tally.true_positives == tally.false_positives == tally.false_negatives == 0)
    ]

    confusion_rows = [
        {
            "expected": expected_decision,
            "aprobar": decision_tally.confusion.get((expected_decision, "APROBAR"), 0),
            "revision": decision_tally.confusion.get((expected_decision, "REVISION"), 0),
            "rechazar": decision_tally.confusion.get((expected_decision, "RECHAZAR"), 0),
        }
        for expected_decision in DECISIONS
    ]

    invoice_cases = [
        {
            "invoice_id": r.factura_id,
            "status": "OK" if r.all_fields_match else "FALLA",
            "detail": r.error or ("; ".join(r.mismatches) if r.mismatches else ""),
        }
        for r in results
    ]

    passed = sum(1 for r in results if r.all_fields_match)

    return {
        "title": "Evals del pipeline completo",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "mode": "live" if live else "mock",
        "summary": f"Grafo completo (docs/spec.md §9): extracción, hallazgos y decisión. {mode_note}",
        "overall_accuracy_pct": round(decision_tally.accuracy * 100, 1),
        "total_cases": len(results),
        "successful_cases": passed,
        "extraction_accuracy": extraction_accuracy,
        "findings_accuracy": findings_accuracy,
        "confusion_matrix": {
            "labels": list(DECISIONS),
            "rows": confusion_rows,
            "accuracy_pct": round(decision_tally.accuracy * 100, 1),
            "correct": decision_tally.correct,
            "total": decision_tally.total,
        },
        "invoice_cases": invoice_cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--mock", action="store_true", help="use fixtures instead of real Azure calls"
    )
    mode.add_argument(
        "--live",
        action="store_true",
        help="call real Azure Document Intelligence + OpenAI (costs money)",
    )
    parser.add_argument(
        "--ids",
        type=str,
        default=None,
        help="comma-separated factura ids to run, e.g. F01,F15 (default: all 15)",
    )
    args = parser.parse_args()

    ground_truth = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    facturas = ground_truth["facturas"]  # already in F01 -> F15 order, see data/README.md

    if args.ids:
        wanted_ids = set(args.ids.split(","))
        facturas = [f for f in facturas if f["id"] in wanted_ids]
        missing = wanted_ids - {f["id"] for f in facturas}
        if missing:
            parser.error(f"unknown factura id(s): {', '.join(sorted(missing))}")

    with SessionLocal() as db:
        seed(db)
        try:
            field_tallies, finding_tallies, decision_tally, results = run(
                db, facturas, live=args.live
            )
        finally:
            # Invoices this run persisted (needed mid-run for F09's duplicate
            # check) would otherwise break `seed()` for anything that runs
            # after this script: Invoice.supplier_id is a real FK, so a
            # leftover row blocks deleting suppliers on the next reseed.
            db.execute(delete(Invoice))
            db.commit()

    report = render_report(field_tallies, finding_tallies, decision_tally, results, live=args.live)
    report_data = build_report_data(field_tallies, finding_tallies, decision_tally, results, live=args.live)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    # --live report filenames include the timestamp and the ids run: --live
    # calls cost real money, so two separate runs on the same day must not
    # silently overwrite each other's evidence the way same-day --mock runs can.
    if args.live:
        ids_suffix = "-" + "-".join(f["id"] for f in facturas) if args.ids else ""
        stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%SZ")
        report_path = REPORTS_DIR / f"{stamp}-live{ids_suffix}.md"
    else:
        report_path = REPORTS_DIR / f"{datetime.now(UTC).date().isoformat()}.md"
    report_path.write_text(report, encoding="utf-8")
    report_path.with_suffix(".json").write_text(
        json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(report)
    print(f"Reporte guardado en {report_path.relative_to(REPO_ROOT)}")

    return 0 if all(r.all_fields_match for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
