import hashlib
from datetime import date
from decimal import Decimal

from app.agents.extract import extract
from app.schemas.extraction import RawField, RawInvoiceExtraction, RawInvoiceLine
from app.services.doc_intelligence import FixtureDocumentIntelligenceClient
from app.services.llm import MockInvoiceLLMClient


def _field(value: str | None, confidence: float = 0.95) -> RawField:
    return RawField(value=value, confidence=confidence)


def _raw_f01() -> RawInvoiceExtraction:
    return RawInvoiceExtraction(
        supplier_nit=_field("900482113-6", confidence=0.97),
        supplier_name=_field("Papelería El Cóndor S.A.S."),
        invoice_number=_field("FEPC 1045", confidence=0.93),
        issue_date=_field("2026-09-01"),
        due_date=_field("2026-10-01"),
        purchase_order=_field("OC-2026-0101"),
        subtotal=_field("740.000,00"),
        vat_total=_field("140.600,00"),
        total=_field("880.600,00", confidence=0.99),
        lines=[
            RawInvoiceLine(
                sku=_field("PAP-001"),
                description=_field("Resma papel carta 75g x500"),
                quantity=_field("40"),
                unit_price=_field("18.500,00"),
                vat_rate=_field("19%"),
                line_subtotal=_field("740.000,00"),
            )
        ],
        full_text=(
            "NIT 900482113-6\n"
            "No. FEPC-1045\n"
            "Consignar a: Bancolombia · Cuenta Ahorros No. 031-458921-77 · Titular: X\n"
            f"CUFE:\n{hashlib.sha384(b'FEPC1045').hexdigest()[:64]}\n"
            f"{hashlib.sha384(b'FEPC1045').hexdigest()[64:]}\n"
        ),
    )


def _client(extraction: RawInvoiceExtraction) -> FixtureDocumentIntelligenceClient:
    pdf_bytes = b"%PDF fake F01"
    file_hash = hashlib.sha256(pdf_bytes).hexdigest()
    return FixtureDocumentIntelligenceClient({file_hash: extraction})


def test_extract_normalizes_and_resolves_f01() -> None:
    pdf_bytes = b"%PDF fake F01"
    extracted, field_confidence = extract(pdf_bytes, _client(_raw_f01()), MockInvoiceLLMClient())

    assert extracted.supplier_nit == "900482113"
    assert extracted.supplier_dv == 6
    assert extracted.supplier_name == "Papelería El Cóndor S.A.S."
    assert extracted.invoice_number == "FEPC-1045"
    assert extracted.issue_date == date(2026, 9, 1)
    assert extracted.due_date == date(2026, 10, 1)
    assert extracted.purchase_order == "OC-2026-0101"
    assert extracted.subtotal == Decimal("740000.00")
    assert extracted.vat_total == Decimal("140600.00")
    assert extracted.total == Decimal("880600.00")
    assert extracted.cufe == hashlib.sha384(b"FEPC1045").hexdigest()
    assert extracted.bank_account is not None
    assert extracted.bank_account.bank == "Bancolombia"

    assert len(extracted.lines) == 1
    line = extracted.lines[0]
    assert line.sku == "PAP-001"
    assert line.quantity == Decimal(40)
    assert line.unit_price == Decimal("18500.00")
    assert line.vat_rate == Decimal(19)
    assert line.line_subtotal == Decimal("740000.00")

    assert field_confidence == {
        "supplier_nit": 0.97,
        "invoice_number": 0.93,
        "total": 0.99,
    }


def test_extract_handles_missing_due_date_and_purchase_order() -> None:
    raw = _raw_f01().model_copy(
        update={"due_date": _field(None), "purchase_order": _field(None)}
    )
    extracted, _ = extract(b"%PDF fake F01", _client(raw), MockInvoiceLLMClient())

    assert extracted.due_date is None
    assert extracted.purchase_order is None
