import re

from app.schemas.finding import Finding, FindingCode
from app.schemas.invoice import ExtractedInvoice

_VALID_CUFE_RE = re.compile(r"^[0-9a-f]{96}$")


def check_cufe(invoice: ExtractedInvoice) -> list[Finding]:
    if invoice.cufe is None or _VALID_CUFE_RE.match(invoice.cufe):
        return []

    return [
        Finding(
            code=FindingCode.INVALID_CUFE,
            severity="ALTA",
            message="El CUFE no tiene 96 caracteres hexadecimales válidos.",
            evidence={"cufe": invoice.cufe, "longitud": len(invoice.cufe)},
        )
    ]
