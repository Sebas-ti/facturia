from datetime import UTC, date, datetime

from app.schemas.finding import Finding, FindingCode
from app.schemas.invoice import ExtractedInvoice


def check_coherent_dates(
    invoice: ExtractedInvoice, processing_date: date | None = None
) -> list[Finding]:
    processing_date = processing_date or datetime.now(UTC).date()
    issues: dict[str, dict[str, str]] = {}

    if invoice.due_date is not None and invoice.due_date < invoice.issue_date:
        issues["fecha_vencimiento_antes_de_emision"] = {
            "fecha_emision": invoice.issue_date.isoformat(),
            "fecha_vencimiento": invoice.due_date.isoformat(),
        }

    if invoice.issue_date > processing_date:
        issues["fecha_emision_futura"] = {
            "fecha_emision": invoice.issue_date.isoformat(),
            "fecha_procesamiento": processing_date.isoformat(),
        }

    if not issues:
        return []

    return [
        Finding(
            code=FindingCode.INCOHERENT_DATES,
            severity="MEDIA",
            message="Las fechas de la factura no son coherentes.",
            evidence=issues,
        )
    ]
