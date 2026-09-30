from decimal import Decimal

from app.rules.matching import check_matching
from app.schemas.finding import FindingCode
from tests.ground_truth import extracted_invoice
from tests.master_data import load_purchase_orders, load_received_quantities

PURCHASE_ORDERS = load_purchase_orders()
RECEIVED_QUANTITY = load_received_quantities()


def test_f01_matches_po_and_receipt_cleanly() -> None:
    findings = check_matching(extracted_invoice("F01"), PURCHASE_ORDERS, RECEIVED_QUANTITY)
    assert findings == []


def test_f07_price_5pct_above_po_is_price_mismatch() -> None:
    findings = check_matching(extracted_invoice("F07"), PURCHASE_ORDERS, RECEIVED_QUANTITY)
    codes = [f.code for f in findings]
    assert codes == [FindingCode.PRICE_MISMATCH]
    assert findings[0].evidence["sku"] == "TEC-402"


def test_f08_ten_toners_but_six_received_is_qty_exceeds_receipt() -> None:
    findings = check_matching(extracted_invoice("F08"), PURCHASE_ORDERS, RECEIVED_QUANTITY)
    codes = [f.code for f in findings]
    assert codes == [FindingCode.QTY_EXCEEDS_RECEIPT]
    assert findings[0].evidence["sku"] == "PAP-031"


def test_f12_missing_po_short_circuits_other_checks() -> None:
    findings = check_matching(extracted_invoice("F12"), PURCHASE_ORDERS, RECEIVED_QUANTITY)
    assert [f.code for f in findings] == [FindingCode.MISSING_PO]


def test_f14_missing_po() -> None:
    findings = check_matching(extracted_invoice("F14"), PURCHASE_ORDERS, RECEIVED_QUANTITY)
    assert [f.code for f in findings] == [FindingCode.MISSING_PO]


def test_referenced_po_that_does_not_exist_is_missing_po() -> None:
    invoice = extracted_invoice("F01").model_copy(update={"purchase_order": "OC-DOES-NOT-EXIST"})
    findings = check_matching(invoice, PURCHASE_ORDERS, RECEIVED_QUANTITY)
    assert [f.code for f in findings] == [FindingCode.MISSING_PO]


def test_accumulated_quantity_from_previous_invoices_counts() -> None:
    invoice = extracted_invoice("F01")
    previously_invoiced = {("OC-2026-0101", "PAP-001"): Decimal(1)}
    findings = check_matching(
        invoice, PURCHASE_ORDERS, RECEIVED_QUANTITY, previously_invoiced
    )
    codes = [f.code for f in findings]
    assert FindingCode.QTY_EXCEEDS_RECEIPT in codes
