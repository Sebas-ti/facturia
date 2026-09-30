from app.rules.arithmetic import check_arithmetic
from app.rules.decision import check_amount_threshold, decide
from app.rules.matching import check_matching
from app.rules.nit import check_nit
from app.rules.risk import (
    check_bank_account_changed,
    check_duplicate_invoice,
    check_unknown_supplier,
)
from app.schemas.finding import Finding
from tests.ground_truth import extracted_invoice, load_facturas
from tests.master_data import load_purchase_orders, load_received_quantities, load_suppliers


def test_all_ground_truth_invoices_match_expected_findings_and_decision() -> None:
    """Recorre F01 -> F15 (ver data/README.md) aplicando todas las reglas juntas."""
    suppliers = load_suppliers()
    purchase_orders = load_purchase_orders()
    received_quantity = load_received_quantities()

    seen_invoice_numbers: set[tuple[str, str]] = set()
    seen_file_hashes: set[str] = set()

    failures: list[str] = []
    for factura in load_facturas():
        invoice = extracted_invoice(factura["id"])
        file_hash = factura["archivo"]

        findings: list[Finding] = [
            *check_nit(invoice),
            *check_arithmetic(invoice),
            *check_matching(invoice, purchase_orders, received_quantity),
            *check_unknown_supplier(invoice, suppliers),
            *check_duplicate_invoice(
                invoice, file_hash, seen_invoice_numbers, seen_file_hashes
            ),
            *check_bank_account_changed(invoice, suppliers),
            *check_amount_threshold(invoice),
        ]
        seen_invoice_numbers.add((invoice.supplier_nit, invoice.invoice_number))
        seen_file_hashes.add(file_hash)

        actual_codes = {f.code.value for f in findings}
        expected_codes = set(factura["hallazgos_esperados"])
        actual_decision = decide(findings)
        expected_decision = factura["decision_esperada"]

        if actual_codes != expected_codes or actual_decision != expected_decision:
            failures.append(
                f"{factura['id']}: hallazgos esperados={sorted(expected_codes)} "
                f"obtenidos={sorted(actual_codes)}; "
                f"decisión esperada={expected_decision} obtenida={actual_decision}"
            )

    assert not failures, "\n" + "\n".join(failures)
