from decimal import Decimal

from app.agents.decide import decide
from app.rules.decision import DEFAULT_AMOUNT_THRESHOLD
from app.schemas.finding import Finding, FindingCode
from app.services.explain import MockDecisionExplainerClient
from tests.ground_truth import extracted_invoice


def test_clean_invoice_under_threshold_is_aprobar() -> None:
    result = decide(extracted_invoice("F01"), [], MockDecisionExplainerClient())
    assert result.decision == "APROBAR"
    assert result.findings == []
    assert result.supplier_email_draft is None


def test_rechazar_when_duplicate_finding_present() -> None:
    duplicate = Finding(
        code=FindingCode.DUPLICATE_INVOICE, severity="CRITICA", message="duplicada", evidence={}
    )
    result = decide(extracted_invoice("F01"), [duplicate], MockDecisionExplainerClient())
    assert result.decision == "RECHAZAR"
    assert result.supplier_email_draft is not None


def test_amount_over_threshold_is_added_and_forces_revision() -> None:
    invoice = extracted_invoice("F01").model_copy(
        update={"total": DEFAULT_AMOUNT_THRESHOLD + Decimal(1)}
    )
    result = decide(invoice, [], MockDecisionExplainerClient())
    assert result.decision == "REVISION"
    assert [f.code for f in result.findings] == [FindingCode.AMOUNT_OVER_THRESHOLD]
