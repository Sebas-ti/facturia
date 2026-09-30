from decimal import Decimal

from app.schemas.finding import Finding, FindingCode
from app.schemas.invoice import ExtractedInvoice

TOLERANCE = Decimal(1)


def check_arithmetic(invoice: ExtractedInvoice) -> list[Finding]:
    lines_subtotal = sum((line.line_subtotal for line in invoice.lines), start=Decimal(0))
    lines_vat = sum(
        (line.line_subtotal * line.vat_rate / Decimal(100) for line in invoice.lines),
        start=Decimal(0),
    )
    subtotal_plus_vat = invoice.subtotal + invoice.vat_total

    mismatches: dict[str, dict[str, str]] = {}
    if abs(lines_subtotal - invoice.subtotal) > TOLERANCE:
        mismatches["lineas_vs_subtotal"] = {
            "suma_lineas": str(lines_subtotal),
            "subtotal_factura": str(invoice.subtotal),
        }
    if abs(lines_vat - invoice.vat_total) > TOLERANCE:
        mismatches["iva_lineas_vs_iva_factura"] = {
            "iva_calculado": str(lines_vat),
            "iva_factura": str(invoice.vat_total),
        }
    if abs(subtotal_plus_vat - invoice.total) > TOLERANCE:
        mismatches["subtotal_mas_iva_vs_total"] = {
            "subtotal_mas_iva": str(subtotal_plus_vat),
            "total_factura": str(invoice.total),
        }

    if not mismatches:
        return []

    return [
        Finding(
            code=FindingCode.ARITHMETIC_ERROR,
            severity="ALTA",
            message="Los valores de la factura no cuadran aritméticamente.",
            evidence=mismatches,
        )
    ]
