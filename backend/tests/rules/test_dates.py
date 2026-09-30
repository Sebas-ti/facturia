from datetime import date

from app.rules.dates import check_coherent_dates
from app.schemas.finding import FindingCode
from tests.ground_truth import extracted_invoice


def test_f01_coherent_dates_has_no_finding() -> None:
    assert check_coherent_dates(extracted_invoice("F01"), processing_date=date(2026, 9, 30)) == []


def test_missing_due_date_has_no_finding() -> None:
    invoice = extracted_invoice("F01").model_copy(update={"due_date": None})
    assert check_coherent_dates(invoice, processing_date=date(2026, 9, 30)) == []


def test_due_date_before_issue_date_is_incoherent() -> None:
    invoice = extracted_invoice("F01").model_copy(update={"due_date": date(2026, 8, 1)})
    findings = check_coherent_dates(invoice, processing_date=date(2026, 9, 30))
    assert [f.code for f in findings] == [FindingCode.INCOHERENT_DATES]
    assert findings[0].severity == "MEDIA"
    assert "fecha_vencimiento_antes_de_emision" in findings[0].evidence


def test_issue_date_after_processing_date_is_incoherent() -> None:
    invoice = extracted_invoice("F01")
    findings = check_coherent_dates(invoice, processing_date=date(2026, 8, 1))
    assert [f.code for f in findings] == [FindingCode.INCOHERENT_DATES]
    assert "fecha_emision_futura" in findings[0].evidence


def test_defaults_to_todays_date_when_processing_date_omitted() -> None:
    invoice = extracted_invoice("F01").model_copy(update={"issue_date": date(2099, 1, 1)})
    findings = check_coherent_dates(invoice)
    assert [f.code for f in findings] == [FindingCode.INCOHERENT_DATES]
