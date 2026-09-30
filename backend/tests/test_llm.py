from app.schemas.extraction import RawField, RawInvoiceExtraction
from app.services.llm import MockInvoiceLLMClient


def _extraction(full_text: str) -> RawInvoiceExtraction:
    field = RawField(value="x", confidence=0.9)
    return RawInvoiceExtraction(
        supplier_nit=field,
        supplier_name=field,
        invoice_number=field,
        issue_date=field,
        due_date=field,
        purchase_order=field,
        subtotal=field,
        vat_total=field,
        total=field,
        lines=[],
        full_text=full_text,
    )


def test_resolves_bank_account_from_consignar_a_line() -> None:
    full_text = (
        "...\nConsignar a: Bancolombia · Cuenta Ahorros No. 031-458921-77 · "
        "Titular: Papelería El Cóndor S.A.S.\n..."
    )
    client = MockInvoiceLLMClient()

    resolved = client.resolve(_extraction(full_text))

    assert resolved.bank_account is not None
    assert resolved.bank_account.bank == "Bancolombia"
    assert resolved.bank_account.account_type == "Ahorros"
    assert resolved.bank_account.number == "031-458921-77"


def test_returns_none_when_absent() -> None:
    client = MockInvoiceLLMClient()

    resolved = client.resolve(_extraction("factura sin esos datos"))

    assert resolved.bank_account is None
