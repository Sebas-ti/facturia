from app.schemas import RawField, RawInvoiceExtraction, RawInvoiceLine


def test_raw_invoice_extraction_round_trips_through_dict() -> None:
    raw_field = RawField(value="1.425.620,00", confidence=0.93)
    extraction = RawInvoiceExtraction(
        supplier_nit=RawField(value="900482113", confidence=0.98),
        supplier_name=RawField(value="Papelería El Cóndor S.A.S.", confidence=0.97),
        invoice_number=RawField(value="FEPC 1045", confidence=0.91),
        issue_date=RawField(value="25/08/2026", confidence=0.95),
        due_date=RawField(value=None, confidence=0.0),
        purchase_order=RawField(value="OC-2026-0101", confidence=0.88),
        subtotal=raw_field,
        vat_total=raw_field,
        total=raw_field,
        lines=[
            RawInvoiceLine(
                sku=RawField(value="PAP-001", confidence=0.9),
                description=RawField(value="Resma papel carta 75g x500", confidence=0.9),
                quantity=RawField(value="40", confidence=0.9),
                unit_price=RawField(value="18.500,00", confidence=0.9),
                vat_rate=RawField(value="19%", confidence=0.9),
                line_subtotal=RawField(value="740.000,00", confidence=0.9),
            )
        ],
        full_text="FEPC 1045 ...",
    )

    assert RawInvoiceExtraction.model_validate(extraction.model_dump()) == extraction
