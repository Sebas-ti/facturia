#!/usr/bin/env python3
"""Extraction evals (docs/spec.md §9): runs `extract` over the sample
invoices (F01 -> F15 by default) and compares the result field-by-field
against data/ground_truth.json, reporting precision per field.

Only extraction is evaluated so far — findings/decision evals land with the
full LangGraph pipeline (Fase 3, see PROGRESS.md). `--mock` uses fixtures
(no Azure calls, no data/facturas/ reads — AGENTS.md rule 6); `--live` calls
the real Azure Document Intelligence + OpenAI clients and reads the real
PDFs, which costs money, so use `--ids` to limit the run (e.g. `--ids
F01,F15`) instead of burning through all 15 invoices by default.
"""

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.agents.extract import extract
from app.schemas.invoice import InvoiceLine
from app.services.doc_intelligence import (
    AzureDocumentIntelligenceClient,
    DocumentIntelligenceClient,
    FixtureDocumentIntelligenceClient,
)
from app.services.llm import AzureInvoiceLLMClient, InvoiceLLMClient, MockInvoiceLLMClient

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


def run(
    facturas: list[dict[str, Any]], *, live: bool
) -> tuple[dict[str, FieldTally], list[InvoiceResult]]:
    tallies: dict[str, FieldTally] = {
        name: FieldTally() for name in (*INVOICE_FIELDS, *LINE_FIELDS)
    }
    results: list[InvoiceResult] = []

    llm_client: InvoiceLLMClient = AzureInvoiceLLMClient() if live else MockInvoiceLLMClient()
    live_doc_client = AzureDocumentIntelligenceClient() if live else None

    for factura in facturas:
        expected = expected_invoice(factura)
        doc_client: DocumentIntelligenceClient
        if live:
            assert live_doc_client is not None
            pdf_bytes = (FACTURAS_DIR / factura["archivo"]).read_bytes()
            doc_client = live_doc_client
        else:
            # mock mode never reads data/facturas/ or calls Azure, see AGENTS.md rule 6
            pdf_bytes = factura["id"].encode()
            file_hash = hashlib.sha256(pdf_bytes).hexdigest()
            doc_client = FixtureDocumentIntelligenceClient(
                {file_hash: build_raw_extraction(factura)}
            )

        try:
            actual, _field_confidence = extract(pdf_bytes, doc_client, llm_client)
        except (ValueError, KeyError) as exc:
            for name in INVOICE_FIELDS:
                tallies[name].record(False)
            for name in LINE_FIELDS:
                for _ in expected.lines:
                    tallies[name].record(False)
            results.append(InvoiceResult(factura["id"], all_fields_match=False, error=str(exc)))
            continue

        mismatches = []
        for field_name in INVOICE_FIELDS:
            actual_value = getattr(actual, field_name)
            expected_value = getattr(expected, field_name)
            is_match = actual_value == expected_value
            tallies[field_name].record(is_match)
            if not is_match:
                mismatches.append(f"{field_name}: {actual_value!r} != {expected_value!r}")

        mismatches += _compare_lines(actual.lines, expected.lines, tallies)
        results.append(
            InvoiceResult(factura["id"], all_fields_match=not mismatches, mismatches=mismatches)
        )

    return tallies, results


def render_report(
    tallies: dict[str, FieldTally], results: list[InvoiceResult], *, live: bool
) -> str:
    mode_note = (
        "Modo `--live`: Azure Document Intelligence + Azure OpenAI reales."
        if live
        else "Modo `--mock`, sin llamadas a Azure."
    )
    lines = [
        "# Evals de extracción",
        "",
        f"Generado: {datetime.now(UTC).isoformat(timespec='seconds')}",
        "",
        (
            "Solo extracción (ver docs/spec.md §9); hallazgos y decisión se evalúan "
            f"cuando exista el grafo completo (Fase 3). {mode_note}"
        ),
        "",
        "## Precisión por campo",
        "",
        "| Campo | Precisión | Aciertos/Total |",
        "|---|---|---|",
    ]
    for name, tally in tallies.items():
        lines.append(f"| `{name}` | {tally.precision:.0%} | {tally.matches}/{tally.total} |")

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

    tallies, results = run(facturas, live=args.live)

    report = render_report(tallies, results, live=args.live)
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

    print(report)
    print(f"Reporte guardado en {report_path.relative_to(REPO_ROOT)}")

    return 0 if all(r.all_fields_match for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
