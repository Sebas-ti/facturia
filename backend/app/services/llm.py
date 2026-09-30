"""Resolves the free-text fields of `extract` that normalize.py can't
handle mechanically: CUFE and bank account (see docs/spec.md §2.1).

The real client (Azure OpenAI, structured outputs) lands in a later task
once Azure credentials are available (PROGRESS.md 2.7). `MockInvoiceLLMClient`
below is a regex-based stand-in: for this project's synthetic, fixed-format
invoices (scripts/generate_data.py) a labeled-line regex is exactly as
reliable as an LLM call would be, and it costs nothing to run in tests/evals.
"""

import re
from typing import Protocol

from app.schemas.extraction import LlmResolvedFields, RawInvoiceExtraction
from app.schemas.invoice import BankAccount

_CUFE_RE = re.compile(r"CUFE:?\s*([0-9a-fA-F\s]{96,150})")
_BANK_ACCOUNT_RE = re.compile(
    r"Consignar a:\s*(?P<bank>[^·]+?)\s*·\s*Cuenta\s+(?P<account_type>Ahorros|Corriente)"
    r"\s+No\.\s*(?P<number>[\w-]+)"
)


class InvoiceLLMClient(Protocol):
    def resolve(self, raw: RawInvoiceExtraction) -> LlmResolvedFields: ...


class MockInvoiceLLMClient:
    def resolve(self, raw: RawInvoiceExtraction) -> LlmResolvedFields:
        return LlmResolvedFields(
            cufe=_extract_cufe(raw.full_text),
            bank_account=_extract_bank_account(raw.full_text),
        )


def _extract_cufe(full_text: str) -> str | None:
    match = _CUFE_RE.search(full_text)
    if match is None:
        return None
    hex_chars = re.sub(r"\s", "", match.group(1))
    return hex_chars[:96] if len(hex_chars) >= 96 else None


def _extract_bank_account(full_text: str) -> BankAccount | None:
    match = _BANK_ACCOUNT_RE.search(full_text)
    if match is None:
        return None
    return BankAccount(
        bank=match.group("bank").strip(),
        account_type=match.group("account_type"),  # type: ignore[arg-type]
        number=match.group("number").strip(),
    )
