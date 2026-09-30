from decimal import Decimal

from app.rules.arithmetic import check_arithmetic
from app.schemas.finding import FindingCode
from app.schemas.invoice import ExtractedInvoice
from tests.ground_truth import extracted_invoice


def test_f01_clean_invoice_has_no_arithmetic_findings() -> None:
    assert check_arithmetic(extracted_invoice("F01")) == []


def test_f10_bad_vat_and_total_raises_arithmetic_error() -> None:
    findings = check_arithmetic(extracted_invoice("F10"))
    assert len(findings) == 1
    assert findings[0].code == FindingCode.ARITHMETIC_ERROR
    assert findings[0].severity == "ALTA"
    assert "iva_lineas_vs_iva_factura" in findings[0].evidence
    assert "subtotal_mas_iva_vs_total" in findings[0].evidence


def test_within_one_peso_tolerance_is_not_an_error() -> None:
    invoice = extracted_invoice("F01").model_copy(update={"total": Decimal("1425620.99")})
    assert check_arithmetic(invoice) == []


def test_more_than_one_peso_off_is_an_error() -> None:
    invoice = extracted_invoice("F01").model_copy(update={"total": Decimal(1425622)})
    findings = check_arithmetic(invoice)
    assert len(findings) == 1
    assert list(findings[0].evidence.keys()) == ["subtotal_mas_iva_vs_total"]


def test_line_subtotals_not_matching_invoice_subtotal_is_an_error() -> None:
    base = extracted_invoice("F01")
    bad_line = base.lines[0].model_copy(update={"line_subtotal": Decimal(999999)})
    invoice = base.model_copy(update={"lines": [bad_line, *base.lines[1:]]})
    findings = check_arithmetic(invoice)
    assert len(findings) == 1
    assert "lineas_vs_subtotal" in findings[0].evidence


def test_invoice_with_no_lines_has_no_negative_arithmetic_error() -> None:
    invoice = ExtractedInvoice(
        supplier_nit="900482113",
        supplier_dv=6,
        supplier_name="Papelería El Cóndor S.A.S.",
        invoice_number="TEST-0001",
        issue_date="2026-01-01",
        due_date=None,
        purchase_order=None,
        currency="COP",
        lines=[],
        subtotal=Decimal(0),
        vat_total=Decimal(0),
        total=Decimal(0),
        cufe=None,
        bank_account=None,
    )
    assert check_arithmetic(invoice) == []
