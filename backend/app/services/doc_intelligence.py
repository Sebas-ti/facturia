"""Client for Azure AI Document Intelligence's prebuilt-invoice model.

See docs/spec.md §2.1. `AzureDocumentIntelligenceClient` is the real client;
`FixtureDocumentIntelligenceClient` is a fixture-backed mock used in tests
and `evals/run_evals.py --mock` so nothing calls Azure there (AGENTS.md rule 6).
"""

import hashlib
import io
from typing import Protocol

from azure.ai.documentintelligence import DocumentIntelligenceClient as _AzureDocIntelClient
from azure.ai.documentintelligence.models import AnalyzeResult, DocumentField
from azure.core.credentials import AzureKeyCredential

from app.config import settings
from app.schemas.extraction import RawField, RawInvoiceExtraction, RawInvoiceLine

# prebuilt-invoice field names, see:
# https://learn.microsoft.com/azure/ai-services/document-intelligence/prebuilt/invoice
_INVOICE_FIELDS = {
    "supplier_nit": "VendorTaxId",
    "supplier_name": "VendorName",
    "invoice_number": "InvoiceId",
    "issue_date": "InvoiceDate",
    "due_date": "DueDate",
    "purchase_order": "PurchaseOrder",
    "subtotal": "SubTotal",
    "vat_total": "TotalTax",
    "total": "InvoiceTotal",
}
_LINE_FIELDS = {
    "sku": "ProductCode",
    "description": "Description",
    "quantity": "Quantity",
    "unit_price": "UnitPrice",
    "vat_rate": "TaxRate",
    "line_subtotal": "Amount",
}


class DocumentIntelligenceClient(Protocol):
    def extract_invoice(self, pdf_bytes: bytes) -> RawInvoiceExtraction: ...


def _raw_field(fields: dict[str, DocumentField], name: str) -> RawField:
    document_field = fields.get(name)
    if document_field is None:
        return RawField(value=None, confidence=0.0)
    return RawField(value=document_field.content, confidence=document_field.confidence or 0.0)


def _raw_line(item_field: DocumentField) -> RawInvoiceLine:
    sub_fields = item_field.value_object or {}
    return RawInvoiceLine(
        **{name: _raw_field(sub_fields, source) for name, source in _LINE_FIELDS.items()}
    )


def _map_result(result: AnalyzeResult) -> RawInvoiceExtraction:
    if not result.documents:
        raise ValueError("Document Intelligence returned no documents for this PDF")

    fields = result.documents[0].fields or {}
    items_field = fields.get("Items")
    items = items_field.value_array if items_field and items_field.value_array else []

    return RawInvoiceExtraction(
        **{name: _raw_field(fields, source) for name, source in _INVOICE_FIELDS.items()},
        lines=[_raw_line(item) for item in items],
        full_text=result.content or "",
    )


class AzureDocumentIntelligenceClient:
    """Real client: calls Azure AI Document Intelligence's prebuilt-invoice
    model. Credentials come from app.config.settings (never hardcoded)."""

    def __init__(self) -> None:
        self._client = _AzureDocIntelClient(
            endpoint=settings.azure_document_intelligence_endpoint,
            credential=AzureKeyCredential(settings.azure_document_intelligence_key),
        )

    def extract_invoice(self, pdf_bytes: bytes) -> RawInvoiceExtraction:
        poller = self._client.begin_analyze_document(
            "prebuilt-invoice", body=io.BytesIO(pdf_bytes), content_type="application/pdf"
        )
        result: AnalyzeResult = poller.result()
        return _map_result(result)


class FixtureDocumentIntelligenceClient:
    """Returns pre-recorded RawInvoiceExtraction fixtures, keyed by the
    SHA-256 of the PDF bytes (matches `ingest`'s file_hash, see spec §2.1)."""

    def __init__(self, fixtures: dict[str, RawInvoiceExtraction]) -> None:
        self._fixtures = fixtures

    def extract_invoice(self, pdf_bytes: bytes) -> RawInvoiceExtraction:
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        try:
            return self._fixtures[file_hash]
        except KeyError:
            raise KeyError(f"No fixture registered for file_hash {file_hash!r}") from None
