"""`validate` node (docs/spec.md §2.1): DV del NIT, aritmética, fechas
coherentes, CUFE — all deterministic rules, no LLM."""

from datetime import date

from app.rules.arithmetic import check_arithmetic
from app.rules.cufe import check_cufe
from app.rules.dates import check_coherent_dates
from app.rules.nit import check_nit
from app.schemas.finding import Finding
from app.schemas.invoice import ExtractedInvoice


def validate(invoice: ExtractedInvoice, processing_date: date | None = None) -> list[Finding]:
    return [
        *check_nit(invoice),
        *check_arithmetic(invoice),
        *check_cufe(invoice),
        *check_coherent_dates(invoice, processing_date),
    ]
