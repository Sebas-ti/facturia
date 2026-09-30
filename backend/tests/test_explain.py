from app.schemas.finding import Finding, FindingCode
from app.services.explain import MockDecisionExplainerClient


def test_aprobar_with_no_findings_has_no_email_draft() -> None:
    result = MockDecisionExplainerClient().explain("APROBAR", [])
    assert result.supplier_email_draft is None
    assert "no presenta hallazgos" in result.explanation


def test_revision_has_no_email_draft() -> None:
    finding = Finding(
        code=FindingCode.PRICE_MISMATCH, severity="MEDIA", message="precio distinto", evidence={}
    )
    result = MockDecisionExplainerClient().explain("REVISION", [finding])
    assert result.supplier_email_draft is None
    assert "precio distinto" in result.explanation


def test_rechazar_has_an_email_draft_mentioning_the_reason() -> None:
    finding = Finding(
        code=FindingCode.ARITHMETIC_ERROR, severity="ALTA", message="el IVA no cuadra", evidence={}
    )
    result = MockDecisionExplainerClient().explain("RECHAZAR", [finding])
    assert result.supplier_email_draft is not None
    assert "el IVA no cuadra" in result.supplier_email_draft
