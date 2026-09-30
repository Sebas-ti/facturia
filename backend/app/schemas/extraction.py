from pydantic import BaseModel

from app.schemas.invoice import BankAccount


class RawField(BaseModel):
    """One field as returned by Document Intelligence's prebuilt-invoice model."""

    value: str | None
    confidence: float


class RawInvoiceLine(BaseModel):
    sku: RawField
    description: RawField
    quantity: RawField
    unit_price: RawField
    vat_rate: RawField
    line_subtotal: RawField


class RawInvoiceExtraction(BaseModel):
    """Unnormalized output of the `extract` node's Document Intelligence step.

    Values are still raw strings (Colombian number format, free-text dates,
    unnormalized invoice numbers) — see docs/spec.md §2.1. `full_text` is the
    document's OCR text, used to find fields prebuilt-invoice doesn't model
    (CUFE, bank account) and to resolve ambiguous free text.
    """

    supplier_nit: RawField
    supplier_name: RawField
    invoice_number: RawField
    issue_date: RawField
    due_date: RawField
    purchase_order: RawField
    subtotal: RawField
    vat_total: RawField
    total: RawField
    lines: list[RawInvoiceLine]
    full_text: str


class LlmResolvedFields(BaseModel):
    """Free-text fields resolved from `full_text` — the only part of `extract`
    that needs an LLM (or, in mock mode, a stand-in), per docs/spec.md §2.1.

    CUFE started out here too, but it's a fixed-length hex string, not
    free text: a live test against real Document Intelligence output showed
    the LLM mistranscribing it when OCR reading order interleaves unrelated
    text (a "QR DIAN" label) between the CUFE's two printed lines. Moved to
    `app.services.normalize.extract_cufe` — mechanical concatenation with a
    fixed stop length has none of that risk (see PROGRESS.md 2.7)."""

    bank_account: BankAccount | None
