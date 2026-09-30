from app.rules.confidence import check_low_confidence
from app.schemas.finding import FindingCode


def test_all_fields_above_threshold_is_clean() -> None:
    field_confidence = {"supplier_nit": 0.95, "invoice_number": 0.99, "total": 0.90}
    assert check_low_confidence(field_confidence) == []


def test_missing_confidence_data_is_clean() -> None:
    assert check_low_confidence({}) == []


def test_critical_field_below_threshold_flags_low_confidence() -> None:
    field_confidence = {"supplier_nit": 0.95, "invoice_number": 0.65, "total": 0.90}
    findings = check_low_confidence(field_confidence)
    assert [f.code for f in findings] == [FindingCode.LOW_CONFIDENCE_EXTRACTION]
    assert findings[0].evidence["campos"] == {"invoice_number": 0.65}


def test_non_critical_field_below_threshold_is_ignored() -> None:
    field_confidence = {"supplier_name": 0.5, "total": 0.90}
    assert check_low_confidence(field_confidence) == []


def test_confidence_exactly_at_threshold_is_clean() -> None:
    field_confidence = {"supplier_nit": 0.80}
    assert check_low_confidence(field_confidence) == []


def test_multiple_low_confidence_fields_are_aggregated_into_one_finding() -> None:
    field_confidence = {"supplier_nit": 0.5, "invoice_number": 0.6, "total": 0.99}
    findings = check_low_confidence(field_confidence)
    assert len(findings) == 1
    assert findings[0].evidence["campos"] == {"supplier_nit": 0.5, "invoice_number": 0.6}
