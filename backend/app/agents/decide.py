"""`decide` node (docs/spec.md §2.1, §4.2): the decision is a deterministic
matrix (app.rules.decision.decide); the LLM only drafts the explanation."""

from dataclasses import dataclass

from app.rules.decision import check_amount_threshold
from app.rules.decision import decide as decide_from_findings
from app.schemas.decision import Decision
from app.schemas.finding import Finding
from app.schemas.invoice import ExtractedInvoice
from app.services.explain import DecisionExplainerClient


@dataclass
class DecideResult:
    findings: list[Finding]  # this node's own new findings (AMOUNT_OVER_THRESHOLD)
    decision: Decision
    explanation: str
    supplier_email_draft: str | None


def decide(
    invoice: ExtractedInvoice,
    findings: list[Finding],
    explainer: DecisionExplainerClient,
) -> DecideResult:
    threshold_findings = check_amount_threshold(invoice)
    all_findings = [*findings, *threshold_findings]
    decision = decide_from_findings(all_findings)
    explanation = explainer.explain(decision, all_findings)

    return DecideResult(
        findings=threshold_findings,
        decision=decision,
        explanation=explanation.explanation,
        supplier_email_draft=explanation.supplier_email_draft,
    )
