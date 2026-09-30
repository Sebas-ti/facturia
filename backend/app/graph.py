"""LangGraph pipeline (docs/spec.md §2). `InvoiceState` is the shared,
persisted state (spec §3); `GraphState` extends it with `pdf_bytes` and
`blob_url`, which the graph needs internally (`ingest` and `extract` both
need the raw bytes) but the spec doesn't persist as part of the invoice
state — they don't belong in a LangGraph checkpoint.

Node order is linear: ingest -> extract -> validate -> match -> risk ->
decide -> human_review. The two "conditional edges" spec §2.1 describes
don't need actual branches here: `LOW_CONFIDENCE_EXTRACTION` is just a
finding the graph doesn't stop for, and `decide` already directly follows
`risk` with no node in between to skip when `DUPLICATE_INVOICE` turns up.

`human_review` is the human-in-the-loop node (spec §2.1's "Nodo de revisión
humana"): when `decide` lands on REVISION, it calls `interrupt()` to pause
the graph — persisted by `checkpointer` (app.services.checkpoint) — until
the analyst's action resumes it via `Command(resume=...)` on the same
thread_id. It's a no-op for APROBAR/RECHAZAR.

`trace=True` wraps every node with app.services.tracing.traced, writing an
AgentRun row per node (spec §5). Off by default because AgentRun.invoice_id
is a real foreign key: the caller must INSERT a placeholder `invoices` row
for `invoice_id` before invoking the graph — that orchestration belongs to
the API layer (Fase 4), not here.
"""

import operator
from collections.abc import Callable
from typing import Annotated, Any, TypedDict
from uuid import UUID

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt
from sqlalchemy.orm import Session

from app.agents.decide import decide as run_decide
from app.agents.extract import extract as run_extract
from app.agents.ingest import ingest as run_ingest
from app.agents.match import match as run_match
from app.agents.risk import risk as run_risk
from app.agents.validate import validate as run_validate
from app.rules.confidence import check_low_confidence
from app.schemas.decision import Decision
from app.schemas.finding import Finding
from app.schemas.invoice import ExtractedInvoice
from app.services.blob import BlobStorageClient
from app.services.doc_intelligence import DocumentIntelligenceClient
from app.services.explain import DecisionExplainerClient
from app.services.llm import InvoiceLLMClient
from app.services.tracing import traced


class InvoiceState(TypedDict):
    invoice_id: UUID
    file_hash: str
    is_scanned: bool
    extracted: ExtractedInvoice | None
    field_confidence: dict[str, float]
    findings: Annotated[list[Finding], operator.add]
    decision: Decision | None
    explanation: str | None
    supplier_email_draft: str | None


class GraphState(InvoiceState):
    pdf_bytes: bytes
    blob_url: str


def build_graph(
    *,
    db: Session,
    doc_intelligence: DocumentIntelligenceClient,
    llm: InvoiceLLMClient,
    blob: BlobStorageClient,
    explainer: DecisionExplainerClient,
    checkpointer: BaseCheckpointSaver[str] | None = None,
    trace: bool = False,
) -> CompiledStateGraph[GraphState, None, GraphState, GraphState]:
    def ingest_node(state: GraphState) -> dict[str, object]:
        result = run_ingest(state["pdf_bytes"], blob)
        return {
            "file_hash": result.file_hash,
            "is_scanned": result.is_scanned,
            "blob_url": result.blob_url,
        }

    def extract_node(state: GraphState) -> dict[str, object]:
        extracted, field_confidence = run_extract(state["pdf_bytes"], doc_intelligence, llm)
        return {
            "extracted": extracted,
            "field_confidence": field_confidence,
            "findings": check_low_confidence(field_confidence),
        }

    def validate_node(state: GraphState) -> dict[str, list[Finding]]:
        assert state["extracted"] is not None
        return {"findings": run_validate(state["extracted"])}

    def match_node(state: GraphState) -> dict[str, list[Finding]]:
        assert state["extracted"] is not None
        return {
            "findings": run_match(
                db, state["extracted"], exclude_invoice_id=state["invoice_id"]
            )
        }

    def risk_node(state: GraphState) -> dict[str, list[Finding]]:
        assert state["extracted"] is not None
        return {
            "findings": run_risk(
                db,
                state["extracted"],
                state["file_hash"],
                exclude_invoice_id=state["invoice_id"],
            )
        }

    def decide_node(state: GraphState) -> dict[str, object]:
        assert state["extracted"] is not None
        result = run_decide(state["extracted"], state["findings"], explainer)
        return {
            "findings": result.findings,
            "decision": result.decision,
            "explanation": result.explanation,
            "supplier_email_draft": result.supplier_email_draft,
        }

    def human_review_node(state: GraphState) -> dict[str, object]:
        if state["decision"] != "REVISION":
            return {}

        analyst_decision = interrupt(
            {
                "invoice_id": str(state["invoice_id"]),
                "decision": state["decision"],
                "explanation": state["explanation"],
            }
        )
        return {"decision": analyst_decision}

    def wrap(name: str, fn: Callable[[GraphState], dict[str, Any]]) -> Any:
        return traced(db, name, fn) if trace else fn

    builder = StateGraph(GraphState)
    builder.add_node("ingest", wrap("ingest", ingest_node))
    builder.add_node("extract", wrap("extract", extract_node))
    builder.add_node("validate", wrap("validate", validate_node))
    builder.add_node("match", wrap("match", match_node))
    builder.add_node("risk", wrap("risk", risk_node))
    builder.add_node("decide", wrap("decide", decide_node))
    builder.add_node("human_review", wrap("human_review", human_review_node))

    builder.add_edge(START, "ingest")
    builder.add_edge("ingest", "extract")
    builder.add_edge("extract", "validate")
    builder.add_edge("validate", "match")
    builder.add_edge("match", "risk")
    builder.add_edge("risk", "decide")
    builder.add_edge("decide", "human_review")
    builder.add_edge("human_review", END)

    return builder.compile(checkpointer=checkpointer)
