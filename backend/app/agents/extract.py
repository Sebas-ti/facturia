"""`extract` node (docs/spec.md §2.1): Document Intelligence -> deterministic
normalization -> LLM (only for bank account) -> ExtractedInvoice.
"""

from app.schemas.extraction import RawField, RawInvoiceLine
from app.schemas.invoice import ExtractedInvoice, InvoiceLine
from app.services.doc_intelligence import DocumentIntelligenceClient
from app.services.llm import InvoiceLLMClient
from app.services.normalize import (
    extract_cufe,
    normalize_invoice_number,
    parse_cop_amount,
    parse_invoice_date,
    split_nit_and_dv,
)

CRITICAL_CONFIDENCE_FIELDS = ("supplier_nit", "invoice_number", "total")

# Placeholders scripts/generate_data.py prints for an absent value; Document
# Intelligence would return this literal text, not a null field.
_EMPTY_SKU_TEXT = ("-", "")
_NO_PO_TEXT = ("—", "N/A")


def extract(
    pdf_bytes: bytes,
    doc_intelligence: DocumentIntelligenceClient,
    llm: InvoiceLLMClient,
) -> tuple[ExtractedInvoice, dict[str, float]]:
    raw = doc_intelligence.extract_invoice(pdf_bytes)
    resolved = llm.resolve(raw)

    nit, dv = split_nit_and_dv(_required(raw.supplier_nit, "supplier_nit"))

    extracted = ExtractedInvoice(
        supplier_nit=nit,
        supplier_dv=dv,
        supplier_name=_required(raw.supplier_name, "supplier_name"),
        invoice_number=normalize_invoice_number(_required(raw.invoice_number, "invoice_number")),
        issue_date=parse_invoice_date(_required(raw.issue_date, "issue_date")),
        due_date=parse_invoice_date(raw.due_date.value) if raw.due_date.value else None,
        purchase_order=_optional(raw.purchase_order.value, _NO_PO_TEXT),
        lines=[_normalize_line(line) for line in raw.lines],
        subtotal=parse_cop_amount(_required(raw.subtotal, "subtotal")),
        vat_total=parse_cop_amount(_required(raw.vat_total, "vat_total")),
        total=parse_cop_amount(_required(raw.total, "total")),
        cufe=extract_cufe(raw.full_text),
        bank_account=resolved.bank_account,
    )

    field_confidence = {
        field: getattr(raw, field).confidence for field in CRITICAL_CONFIDENCE_FIELDS
    }

    return extracted, field_confidence


def _normalize_line(line: RawInvoiceLine) -> InvoiceLine:
    return InvoiceLine(
        sku=_optional(line.sku.value, _EMPTY_SKU_TEXT),
        description=_required(line.description, "lines[].description"),
        quantity=parse_cop_amount(_required(line.quantity, "lines[].quantity")),
        unit_price=parse_cop_amount(_required(line.unit_price, "lines[].unit_price")),
        vat_rate=parse_cop_amount(_required(line.vat_rate, "lines[].vat_rate")),
        line_subtotal=parse_cop_amount(_required(line.line_subtotal, "lines[].line_subtotal")),
    )


def _required(field: RawField, name: str) -> str:
    if field.value is None:
        raise ValueError(f"Missing required field: {name}")
    return field.value


def _optional(value: str | None, placeholders: tuple[str, ...]) -> str | None:
    return None if value is None or value in placeholders else value
