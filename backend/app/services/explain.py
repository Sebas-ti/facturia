"""Writes the analyst-facing explanation and, when rejecting, the supplier
email draft for the `decide` node (docs/spec.md §2.1, §4.2). The decision
itself is already final by the time this runs — the LLM only explains it in
words, never influences it.
"""

from typing import Protocol

from openai import AzureOpenAI
from pydantic import BaseModel

from app.config import settings
from app.schemas.decision import Decision
from app.schemas.finding import Finding

_SYSTEM_PROMPT = (
    "Eres un asistente de cuentas por pagar. Te dan la decisión ya tomada "
    "(APROBAR, REVISION o RECHAZAR) sobre una factura de proveedor y la lista "
    "de hallazgos que la motivaron. Escribe una explicación breve y clara en "
    "español para el analista que revisará la factura. Si la decisión es "
    "RECHAZAR, escribe también un borrador de correo cordial y profesional "
    "para el proveedor pidiendo una nota crédito o una factura corregida, "
    "mencionando el motivo; si no es RECHAZAR, deja el correo como null. No "
    "cambies ni cuestiones la decisión — solo explícala."
)


class DecisionExplanation(BaseModel):
    explanation: str
    supplier_email_draft: str | None


class DecisionExplainerClient(Protocol):
    def explain(self, decision: Decision, findings: list[Finding]) -> DecisionExplanation: ...


class AzureDecisionExplainerClient:
    """Real client: Azure OpenAI with structured outputs. Credentials come
    from app.config.settings (never hardcoded)."""

    def __init__(self) -> None:
        self._client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_key,
            api_version=settings.azure_openai_api_version,
        )

    def explain(self, decision: Decision, findings: list[Finding]) -> DecisionExplanation:
        findings_text = (
            "\n".join(f"- [{f.severity}] {f.code.value}: {f.message}" for f in findings)
            or "(sin hallazgos)"
        )
        completion = self._client.chat.completions.parse(
            model=settings.azure_openai_deployment,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Decisión: {decision}\nHallazgos:\n{findings_text}"},
            ],
            response_format=DecisionExplanation,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("Azure OpenAI returned no structured output")
        return parsed


class MockDecisionExplainerClient:
    """Deterministic, template-based explanation — no LLM call, used in
    tests/evals (AGENTS.md rule 6)."""

    def explain(self, decision: Decision, findings: list[Finding]) -> DecisionExplanation:
        if not findings:
            explanation = "La factura no presenta hallazgos y cumple todas las validaciones."
        else:
            bullet_points = "\n".join(f"- [{f.severity}] {f.message}" for f in findings)
            explanation = f"Decisión {decision} por los siguientes hallazgos:\n{bullet_points}"

        supplier_email_draft = None
        if decision == "RECHAZAR":
            reasons = "; ".join(f.message for f in findings)
            supplier_email_draft = (
                "Estimado proveedor,\n\n"
                "No podemos procesar esta factura por lo siguiente: "
                f"{reasons}. Por favor envíe una nota crédito o una factura "
                "corregida.\n\nSaludos,\nCuentas por Pagar"
            )

        return DecisionExplanation(
            explanation=explanation, supplier_email_draft=supplier_email_draft
        )
