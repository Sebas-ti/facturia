from datetime import date

from app.agents.validate import validate
from app.schemas.finding import FindingCode
from tests.ground_truth import extracted_invoice


def test_f01_clean_invoice_has_no_findings() -> None:
    assert validate(extracted_invoice("F01"), processing_date=date(2026, 9, 30)) == []


def test_f10_arithmetic_error_is_caught() -> None:
    findings = validate(extracted_invoice("F10"), processing_date=date(2026, 9, 30))
    assert FindingCode.ARITHMETIC_ERROR in [f.code for f in findings]


def test_f11_invalid_nit_dv_is_caught() -> None:
    findings = validate(extracted_invoice("F11"), processing_date=date(2026, 9, 30))
    assert FindingCode.INVALID_NIT_DV in [f.code for f in findings]


def test_combines_multiple_findings() -> None:
    invoice = extracted_invoice("F01").model_copy(
        update={"cufe": "not-a-cufe", "due_date": date(2026, 1, 1)}
    )
    findings = validate(invoice, processing_date=date(2026, 9, 30))
    codes = {f.code for f in findings}
    assert codes == {FindingCode.INVALID_CUFE, FindingCode.INCOHERENT_DATES}
