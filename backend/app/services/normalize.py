"""Deterministic normalization of raw Document Intelligence field values.

See docs/spec.md §2.1: Colombian number format, invoice number prefix/number
and dates are mechanical transformations, not LLM work — kept here as pure,
testable code per AGENTS.md rule 1.
"""

import re
from datetime import date
from decimal import Decimal

_AMOUNT_CLEAN_RE = re.compile(r"[^\d.,\-]")
_INVOICE_NUMBER_RE = re.compile(r"([A-Z]{2,6})\D{0,3}(\d{3,})")
_ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_SLASH_OR_DASH_DATE_RE = re.compile(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$")
_NIT_DV_RE = re.compile(r"(\d{6,15})(?:\D+(\d))?\s*$")


def parse_cop_amount(raw: str) -> Decimal:
    """Parse a Colombian-formatted amount, e.g. "$ 1.425.620,00" -> Decimal("1425620.00").

    Colombian format uses '.' as the thousands separator and ',' as the
    decimal separator. A lone '.' is ambiguous (thousands vs. decimal point),
    so it's treated as a thousands separator only when followed by exactly
    3 digits at the end of the string (e.g. "18.500" -> 18500, but
    "40.5" stays 40.5).
    """
    cleaned = _AMOUNT_CLEAN_RE.sub("", raw).strip()
    if not cleaned.lstrip("-"):
        raise ValueError(f"Empty amount: {raw!r}")

    negative = cleaned.startswith("-")
    cleaned = cleaned.lstrip("-")

    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "." in cleaned:
        integer_part, _, last_group = cleaned.rpartition(".")
        if integer_part and len(last_group) == 3:
            cleaned = cleaned.replace(".", "")

    value = Decimal(cleaned)
    return -value if negative else value


def normalize_invoice_number(raw: str) -> str:
    """Normalize a raw invoice number to "PREFIJO-NUMERO".

    Handles the raw forms noted in data/README.md: "FEPC 1045",
    "No. TRS-20871", "LTV11502" all normalize to "FEPC-1045", "TRS-20871",
    "LTV-11502".
    """
    match = _INVOICE_NUMBER_RE.search(raw.upper())
    if match is None:
        raise ValueError(f"Could not normalize invoice number: {raw!r}")
    prefix, number = match.groups()
    return f"{prefix}-{number}"


def parse_invoice_date(raw: str) -> date:
    """Parse a date in ISO (YYYY-MM-DD) or DD/MM/YYYY / DD-MM-YYYY form."""
    raw = raw.strip()

    if _ISO_DATE_RE.match(raw):
        return date.fromisoformat(raw)

    match = _SLASH_OR_DASH_DATE_RE.match(raw)
    if match:
        day, month, year = (int(part) for part in match.groups())
        return date(year, month, day)

    raise ValueError(f"Could not parse date: {raw!r}")


def split_nit_and_dv(raw: str) -> tuple[str, int | None]:
    """Split a printed "NIT-DV" string, e.g. "900482113-6" or "900482113 - 6",
    into (nit, dv). `dv` is None if the raw text has no trailing check digit.
    """
    match = _NIT_DV_RE.search(raw.strip())
    if match is None:
        raise ValueError(f"Could not parse NIT: {raw!r}")
    nit, dv = match.groups()
    return nit, int(dv) if dv is not None else None
