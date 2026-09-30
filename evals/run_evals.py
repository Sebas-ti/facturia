#!/usr/bin/env python3
"""Extraction evals (docs/spec.md §9): runs `extract` over the 15 sample
invoices (F01 -> F15) and compares the result field-by-field against
data/ground_truth.json, reporting precision per field.

Only extraction is evaluated so far — findings/decision evals land with the
full LangGraph pipeline (Fase 3, see PROGRESS.md). `--mock` is the only mode
today: there's no real Azure Document Intelligence / OpenAI client yet
(PROGRESS.md 2.7), and AGENTS.md rule 6 says not to call Azure or read the
PDFs unless the task requires it.
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
from app.services.doc_intelligence import FixtureDocumentIntelligenceClient
from app.services.llm import MockInvoiceLLMClient

REPO_ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH_PATH = REPO_ROOT / "data" / "ground_truth.json"
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


def run(facturas: list[dict[str, Any]]) -> tuple[dict[str, FieldTally], list[InvoiceResult]]:
    tallies: dict[str, FieldTally] = {
        name: FieldTally() for name in (*INVOICE_FIELDS, *LINE_FIELDS)
    }
    results: list[InvoiceResult] = []

    for factura in facturas:
        expected = expected_invoice(factura)
        pdf_bytes = factura["id"].encode()  # mock mode never reads data/facturas/, see AGENTS.md rule 6
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        client = FixtureDocumentIntelligenceClient({file_hash: build_raw_extraction(factura)})

        try:
            actual, _field_confidence = extract(pdf_bytes, client, MockInvoiceLLMClient())
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


def render_report(tallies: dict[str, FieldTally], results: list[InvoiceResult]) -> str:
    lines = [
        "# Evals de extracción",
        "",
        f"Generado: {datetime.now(UTC).isoformat(timespec='seconds')}",
        "",
        (
            "Solo extracción (ver docs/spec.md §9); hallazgos y decisión se evalúan "
            "cuando exista el grafo completo (Fase 3). Modo `--mock`, sin llamadas a Azure."
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
    parser.add_argument(
        "--mock", action="store_true", help="use fixtures instead of real Azure calls"
    )
    args = parser.parse_args()

    if not args.mock:
        parser.error(
            "only --mock is supported today; the real Azure client lands in "
            "PROGRESS.md task 2.7"
        )

    ground_truth = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    facturas = ground_truth["facturas"]  # already in F01 -> F15 order, see data/README.md

    tallies, results = run(facturas)

    report = render_report(tallies, results)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"{datetime.now(UTC).date().isoformat()}.md"
    report_path.write_text(report, encoding="utf-8")

    print(report)
    print(f"Reporte guardado en {report_path.relative_to(REPO_ROOT)}")

    return 0 if all(r.all_fields_match for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
