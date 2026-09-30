from app.rules.cufe import check_cufe
from app.schemas.finding import FindingCode
from tests.ground_truth import extracted_invoice


def test_f01_valid_cufe_has_no_finding() -> None:
    assert check_cufe(extracted_invoice("F01")) == []


def test_missing_cufe_has_no_finding() -> None:
    invoice = extracted_invoice("F01").model_copy(update={"cufe": None})
    assert check_cufe(invoice) == []


def test_short_cufe_is_invalid() -> None:
    invoice = extracted_invoice("F01").model_copy(update={"cufe": "abc123"})
    findings = check_cufe(invoice)
    assert [f.code for f in findings] == [FindingCode.INVALID_CUFE]
    assert findings[0].severity == "ALTA"
    assert findings[0].evidence["longitud"] == 6


def test_uppercase_cufe_is_invalid() -> None:
    valid_cufe = extracted_invoice("F01").cufe
    assert valid_cufe is not None
    invoice = extracted_invoice("F01").model_copy(update={"cufe": valid_cufe.upper()})
    assert [f.code for f in check_cufe(invoice)] == [FindingCode.INVALID_CUFE]


def test_non_hex_characters_are_invalid() -> None:
    invoice = extracted_invoice("F01").model_copy(update={"cufe": "g" * 96})
    assert [f.code for f in check_cufe(invoice)] == [FindingCode.INVALID_CUFE]
