from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel

Severity = Literal["INFO", "MEDIA", "ALTA", "CRITICA"]


class FindingCode(StrEnum):
    INVALID_NIT_DV = "INVALID_NIT_DV"
    ARITHMETIC_ERROR = "ARITHMETIC_ERROR"
    INVALID_CUFE = "INVALID_CUFE"
    INCOHERENT_DATES = "INCOHERENT_DATES"
    UNKNOWN_SUPPLIER = "UNKNOWN_SUPPLIER"
    MISSING_PO = "MISSING_PO"
    PRICE_MISMATCH = "PRICE_MISMATCH"
    QTY_EXCEEDS_RECEIPT = "QTY_EXCEEDS_RECEIPT"
    DUPLICATE_INVOICE = "DUPLICATE_INVOICE"
    BANK_ACCOUNT_CHANGED = "BANK_ACCOUNT_CHANGED"
    LOW_CONFIDENCE_EXTRACTION = "LOW_CONFIDENCE_EXTRACTION"
    AMOUNT_OVER_THRESHOLD = "AMOUNT_OVER_THRESHOLD"


class Finding(BaseModel):
    code: FindingCode
    severity: Severity
    message: str
    evidence: dict[str, Any]
