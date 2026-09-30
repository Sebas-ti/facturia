from app.schemas.finding import Finding, FindingCode
from app.schemas.invoice import ExtractedInvoice

# DIAN módulo 11 check digit, see docs/spec.md §4.3.
WEIGHTS = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]


def nit_check_digit(nit: str) -> int:
    if not 1 <= len(nit) <= len(WEIGHTS):
        raise ValueError(f"NIT must be 1-{len(WEIGHTS)} digits long: {nit!r}")
    if not nit.isdigit():
        raise ValueError(f"NIT must contain only digits: {nit!r}")

    r = sum(int(digit) * WEIGHTS[i] for i, digit in enumerate(reversed(nit))) % 11
    return r if r in (0, 1) else 11 - r


def validate_nit(nit: str, dv: int) -> bool:
    return nit_check_digit(nit) == dv


def check_nit(invoice: ExtractedInvoice) -> list[Finding]:
    if invoice.supplier_dv is None or validate_nit(invoice.supplier_nit, invoice.supplier_dv):
        return []

    return [
        Finding(
            code=FindingCode.INVALID_NIT_DV,
            severity="ALTA",
            message="El DV impreso no coincide con el DV calculado del NIT.",
            evidence={
                "nit": invoice.supplier_nit,
                "dv_impreso": invoice.supplier_dv,
                "dv_calculado": nit_check_digit(invoice.supplier_nit),
            },
        )
    ]
