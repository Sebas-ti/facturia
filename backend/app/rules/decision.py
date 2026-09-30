from decimal import Decimal

from app.schemas.decision import Decision
from app.schemas.finding import Finding, FindingCode
from app.schemas.invoice import ExtractedInvoice

DEFAULT_AMOUNT_THRESHOLD = Decimal(20_000_000)

_RECHAZAR_CODES = {FindingCode.DUPLICATE_INVOICE, FindingCode.ARITHMETIC_ERROR}
_REVISION_SEVERITIES = {"MEDIA", "ALTA", "CRITICA"}


def check_amount_threshold(
    invoice: ExtractedInvoice, threshold: Decimal = DEFAULT_AMOUNT_THRESHOLD
) -> list[Finding]:
    if invoice.total <= threshold:
        return []

    return [
        Finding(
            code=FindingCode.AMOUNT_OVER_THRESHOLD,
            severity="INFO",
            message="El total supera el umbral de aprobación automática.",
            evidence={"total": str(invoice.total), "umbral": str(threshold)},
        )
    ]


def decide(findings: list[Finding]) -> Decision:
    codes = {f.code for f in findings}

    if codes & _RECHAZAR_CODES:
        return "RECHAZAR"
    if FindingCode.AMOUNT_OVER_THRESHOLD in codes:
        return "REVISION"
    if any(f.severity in _REVISION_SEVERITIES for f in findings):
        return "REVISION"

    return "APROBAR"
