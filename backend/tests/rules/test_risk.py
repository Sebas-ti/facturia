from app.rules.risk import (
    check_bank_account_changed,
    check_duplicate_invoice,
    check_unknown_supplier,
)
from app.schemas.finding import FindingCode
from tests.ground_truth import extracted_invoice
from tests.master_data import load_suppliers

SUPPLIERS = load_suppliers()


def test_f01_known_active_supplier_has_no_findings() -> None:
    assert check_unknown_supplier(extracted_invoice("F01"), SUPPLIERS) == []


def test_f12_supplier_not_in_master_is_unknown_supplier() -> None:
    findings = check_unknown_supplier(extracted_invoice("F12"), SUPPLIERS)
    assert [f.code for f in findings] == [FindingCode.UNKNOWN_SUPPLIER]
    assert findings[0].evidence["encontrado"] is False


def test_inactive_supplier_is_unknown_supplier() -> None:
    inactive_suppliers = {
        nit: supplier.model_copy(update={"status": "INACTIVO"})
        for nit, supplier in SUPPLIERS.items()
    }
    findings = check_unknown_supplier(extracted_invoice("F01"), inactive_suppliers)
    assert [f.code for f in findings] == [FindingCode.UNKNOWN_SUPPLIER]
    assert findings[0].evidence["encontrado"] is True


def test_f01_first_time_seen_is_not_a_duplicate() -> None:
    findings = check_duplicate_invoice(
        extracted_invoice("F01"), file_hash="hash-f01", previous_invoice_numbers=set(),
        previous_file_hashes=set(),
    )
    assert findings == []


def test_f09_same_nit_and_number_as_f01_is_duplicate() -> None:
    f01 = extracted_invoice("F01")
    findings = check_duplicate_invoice(
        extracted_invoice("F09"),
        file_hash="hash-f09",
        previous_invoice_numbers={(f01.supplier_nit, f01.invoice_number)},
        previous_file_hashes={"hash-f01"},
    )
    assert [f.code for f in findings] == [FindingCode.DUPLICATE_INVOICE]
    assert findings[0].evidence["mismo_numero"] is True
    assert findings[0].evidence["mismo_hash"] is False


def test_same_file_hash_is_duplicate_even_with_different_invoice_number() -> None:
    findings = check_duplicate_invoice(
        extracted_invoice("F02"),
        file_hash="hash-f01",
        previous_invoice_numbers=set(),
        previous_file_hashes={"hash-f01"},
    )
    assert [f.code for f in findings] == [FindingCode.DUPLICATE_INVOICE]
    assert findings[0].evidence["mismo_hash"] is True


def test_f01_bank_account_matches_registered_one() -> None:
    assert check_bank_account_changed(extracted_invoice("F01"), SUPPLIERS) == []


def test_f13_bank_account_differs_from_registered_one() -> None:
    findings = check_bank_account_changed(extracted_invoice("F13"), SUPPLIERS)
    assert [f.code for f in findings] == [FindingCode.BANK_ACCOUNT_CHANGED]
    assert findings[0].severity == "CRITICA"
