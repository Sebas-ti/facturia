"""Resolves the one free-text field of `extract` that normalize.py can't
handle mechanically: the provider's bank account (see docs/spec.md §2.1).
CUFE also comes from `full_text`, but deterministically — see
app.services.normalize.extract_cufe.

`AzureInvoiceLLMClient` is the real client (Azure OpenAI, structured
outputs). `MockInvoiceLLMClient` is a regex-based stand-in: for this
project's synthetic, fixed-format invoices (scripts/generate_data.py) a
labeled-line regex is exactly as reliable as an LLM call would be, and it
costs nothing to run in tests/evals (AGENTS.md rule 6).
"""

import re
from typing import Protocol

from openai import AzureOpenAI

from app.config import settings
from app.schemas.extraction import LlmResolvedFields, RawInvoiceExtraction
from app.schemas.invoice import BankAccount

_BANK_ACCOUNT_RE = re.compile(
    r"Consignar a:\s*(?P<bank>[^·]+?)\s*·\s*Cuenta\s+(?P<account_type>Ahorros|Corriente)"
    r"\s+No\.\s*(?P<number>[\w-]+)"
)
_SYSTEM_PROMPT = (
    "Extraes la cuenta bancaria del proveedor para pagos (banco, tipo 'Ahorros' o "
    "'Corriente', número de cuenta) del texto OCR de una factura electrónica "
    "colombiana. Si no aparece en el texto, devuélvela como null. No inventes datos."
)


class InvoiceLLMClient(Protocol):
    def resolve(self, raw: RawInvoiceExtraction) -> LlmResolvedFields: ...


class AzureInvoiceLLMClient:
    """Real client: Azure OpenAI with structured outputs (Pydantic schema).
    Credentials come from app.config.settings (never hardcoded)."""

    def __init__(self) -> None:
        self._client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_key,
            api_version=settings.azure_openai_api_version,
        )

    def resolve(self, raw: RawInvoiceExtraction) -> LlmResolvedFields:
        completion = self._client.chat.completions.parse(
            model=settings.azure_openai_deployment,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": raw.full_text},
            ],
            response_format=LlmResolvedFields,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("Azure OpenAI returned no structured output")
        return parsed


class MockInvoiceLLMClient:
    def resolve(self, raw: RawInvoiceExtraction) -> LlmResolvedFields:
        return LlmResolvedFields(bank_account=_extract_bank_account(raw.full_text))


def _extract_bank_account(full_text: str) -> BankAccount | None:
    match = _BANK_ACCOUNT_RE.search(full_text)
    if match is None:
        return None
    return BankAccount(
        bank=match.group("bank").strip(),
        account_type=match.group("account_type"),  # type: ignore[arg-type]
        number=match.group("number").strip(),
    )
