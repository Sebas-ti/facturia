from datetime import date
from decimal import Decimal
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.graph import InvoiceState
from app.schemas.finding import Finding, FindingCode
from app.schemas.invoice import ExtractedInvoice


def _extracted_invoice() -> ExtractedInvoice:
    return ExtractedInvoice(
        supplier_nit="900482113",
        supplier_dv=6,
        supplier_name="Papelería El Cóndor S.A.S.",
        invoice_number="FEPC-1045",
        issue_date=date(2026, 9, 1),
        due_date=date(2026, 10, 1),
        purchase_order="OC-2026-0101",
        lines=[],
        subtotal=Decimal(0),
        vat_total=Decimal(0),
        total=Decimal(0),
        cufe=None,
        bank_account=None,
    )


def test_invoice_state_accepts_the_spec_3_shape() -> None:
    state: InvoiceState = {
        "invoice_id": uuid4(),
        "file_hash": "abc123",
        "is_scanned": False,
        "extracted": _extracted_invoice(),
        "field_confidence": {"supplier_nit": 0.97},
        "findings": [],
        "decision": None,
        "explanation": None,
        "supplier_email_draft": None,
    }

    assert state["extracted"] is not None
    assert state["extracted"].supplier_nit == "900482113"


def test_findings_accumulate_across_nodes_via_the_operator_add_reducer() -> None:
    """Two nodes each contribute a Finding; neither node's output should
    erase the other's, per docs/spec.md §3: "ningún nodo borra lo de otro"."""

    def node_a(_state: InvoiceState) -> dict[str, list[Finding]]:
        return {
            "findings": [
                Finding(
                    code=FindingCode.MISSING_PO,
                    severity="MEDIA",
                    message="a",
                    evidence={},
                )
            ]
        }

    def node_b(_state: InvoiceState) -> dict[str, list[Finding]]:
        return {
            "findings": [
                Finding(
                    code=FindingCode.UNKNOWN_SUPPLIER,
                    severity="ALTA",
                    message="b",
                    evidence={},
                )
            ]
        }

    builder = StateGraph(InvoiceState)
    builder.add_node("node_a", node_a)
    builder.add_node("node_b", node_b)
    builder.add_edge(START, "node_a")
    builder.add_edge("node_a", "node_b")
    builder.add_edge("node_b", END)
    graph = builder.compile()

    result = graph.invoke(
        {
            "invoice_id": uuid4(),
            "file_hash": "abc123",
            "is_scanned": False,
            "extracted": None,
            "field_confidence": {},
            "findings": [],
            "decision": None,
            "explanation": None,
            "supplier_email_draft": None,
        }
    )

    codes = {f.code for f in result["findings"]}
    assert codes == {FindingCode.MISSING_PO, FindingCode.UNKNOWN_SUPPLIER}
