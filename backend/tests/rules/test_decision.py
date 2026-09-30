from decimal import Decimal

from app.rules.decision import check_amount_threshold, decide
from app.schemas.finding import Finding, FindingCode
from tests.ground_truth import extracted_invoice


def _finding(code: FindingCode, severity: str) -> Finding:
    return Finding(code=code, severity=severity, message="test", evidence={})


def test_no_findings_is_aprobar() -> None:
    assert decide([]) == "APROBAR"


def test_duplicate_invoice_is_rechazar() -> None:
    assert decide([_finding(FindingCode.DUPLICATE_INVOICE, "CRITICA")]) == "RECHAZAR"


def test_arithmetic_error_is_rechazar() -> None:
    assert decide([_finding(FindingCode.ARITHMETIC_ERROR, "ALTA")]) == "RECHAZAR"


def test_rechazar_takes_priority_over_other_findings() -> None:
    findings = [
        _finding(FindingCode.ARITHMETIC_ERROR, "ALTA"),
        _finding(FindingCode.BANK_ACCOUNT_CHANGED, "CRITICA"),
    ]
    assert decide(findings) == "RECHAZAR"


def test_medium_severity_finding_is_revision() -> None:
    assert decide([_finding(FindingCode.PRICE_MISMATCH, "MEDIA")]) == "REVISION"


def test_critica_finding_is_revision_not_rechazar() -> None:
    # BANK_ACCOUNT_CHANGED es CRITICA pero no está en la lista de rechazo automático.
    assert decide([_finding(FindingCode.BANK_ACCOUNT_CHANGED, "CRITICA")]) == "REVISION"


def test_amount_over_threshold_is_revision_even_though_it_is_info() -> None:
    assert decide([_finding(FindingCode.AMOUNT_OVER_THRESHOLD, "INFO")]) == "REVISION"


def test_info_finding_other_than_amount_threshold_is_aprobar() -> None:
    assert decide([_finding(FindingCode.MISSING_PO, "INFO")]) == "APROBAR"


def test_check_amount_threshold_below_default_has_no_finding() -> None:
    invoice = extracted_invoice("F01")  # total 1,425,620 < 20,000,000
    assert check_amount_threshold(invoice) == []


def test_check_amount_threshold_above_default_flags_it() -> None:
    invoice = extracted_invoice("F01").model_copy(update={"total": Decimal(20000001)})
    findings = check_amount_threshold(invoice)
    assert [f.code for f in findings] == [FindingCode.AMOUNT_OVER_THRESHOLD]
    assert findings[0].severity == "INFO"


def test_check_amount_threshold_exactly_at_threshold_has_no_finding() -> None:
    invoice = extracted_invoice("F01").model_copy(update={"total": Decimal(20000000)})
    assert check_amount_threshold(invoice) == []
