import hashlib

import pytest

from app.schemas.extraction import RawField, RawInvoiceExtraction
from app.services.doc_intelligence import FixtureDocumentIntelligenceClient


def _raw_field(value: str = "x") -> RawField:
    return RawField(value=value, confidence=0.9)


def _extraction() -> RawInvoiceExtraction:
    return RawInvoiceExtraction(
        supplier_nit=_raw_field("900482113"),
        supplier_name=_raw_field("Papelería El Cóndor S.A.S."),
        invoice_number=_raw_field("FEPC 1045"),
        issue_date=_raw_field("2026-09-01"),
        due_date=_raw_field("2026-10-01"),
        purchase_order=_raw_field("OC-2026-0101"),
        subtotal=_raw_field("740.000,00"),
        vat_total=_raw_field("140.600,00"),
        total=_raw_field("880.600,00"),
        lines=[],
        full_text="...",
    )


def test_fixture_client_returns_extraction_by_file_hash() -> None:
    pdf_bytes = b"%PDF-1.4 fake invoice"
    file_hash = hashlib.sha256(pdf_bytes).hexdigest()
    extraction = _extraction()
    client = FixtureDocumentIntelligenceClient({file_hash: extraction})

    assert client.extract_invoice(pdf_bytes) == extraction


def test_fixture_client_raises_for_unregistered_file() -> None:
    client = FixtureDocumentIntelligenceClient({})
    with pytest.raises(KeyError, match="No fixture registered"):
        client.extract_invoice(b"unknown pdf bytes")
