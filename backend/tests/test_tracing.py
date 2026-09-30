import hashlib
from collections.abc import Generator
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import AgentRun, Invoice
from app.db.session import SessionLocal
from app.graph import GraphState, build_graph
from app.schemas.extraction import RawField, RawInvoiceExtraction, RawInvoiceLine
from app.services.blob import BlobStorageClient
from app.services.doc_intelligence import FixtureDocumentIntelligenceClient
from app.services.explain import MockDecisionExplainerClient
from app.services.llm import MockInvoiceLLMClient
from scripts.seed import seed

DATA_DIR = Path(__file__).parents[2] / "data"


def _field(value: str | None, confidence: float = 0.95) -> RawField:
    return RawField(value=value, confidence=confidence)


def _raw_f01() -> RawInvoiceExtraction:
    cufe = hashlib.sha384(b"FEPC1045").hexdigest()
    return RawInvoiceExtraction(
        supplier_nit=_field("900482113-6", confidence=0.97),
        supplier_name=_field("Papelería El Cóndor S.A.S."),
        invoice_number=_field("FEPC 1045", confidence=0.93),
        issue_date=_field("2026-09-01"),
        due_date=_field("2026-10-01"),
        purchase_order=_field("OC-2026-0101"),
        subtotal=_field("740.000,00"),
        vat_total=_field("140.600,00"),
        total=_field("880.600,00", confidence=0.99),
        lines=[
            RawInvoiceLine(
                sku=_field("PAP-001"),
                description=_field("Resma papel carta 75g x500"),
                quantity=_field("40"),
                unit_price=_field("18.500,00"),
                vat_rate=_field("19%"),
                line_subtotal=_field("740.000,00"),
            )
        ],
        full_text=(
            "Consignar a: Bancolombia · Cuenta Ahorros No. 031-458921-77 · Titular: X\n"
            f"CUFE:\n{cufe[:64]}\n{cufe[64:]}\n"
        ),
    )


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Requires `docker compose up -d db azurite` and `alembic upgrade head`
    (see AGENTS.md)."""
    with SessionLocal() as session:
        seed(session)
        yield session


def test_trace_true_writes_one_agent_run_row_per_node(db: Session) -> None:
    pdf_bytes = (DATA_DIR / "facturas" / "F01_FEPC-1045.pdf").read_bytes()
    file_hash = hashlib.sha256(pdf_bytes).hexdigest()
    doc_intelligence = FixtureDocumentIntelligenceClient({file_hash: _raw_f01()})

    invoice_id = uuid4()
    # Placeholder row: AgentRun.invoice_id is a real FK, so it must exist
    # before the graph runs. A real caller (Fase 4's API layer) would do
    # this before invoking the graph and update it with the final result.
    db.add(
        Invoice(
            id=invoice_id,
            file_hash="pending",
            blob_url="pending",
            status="PROCESSING",
            supplier_id=None,
            invoice_number="pending",
            total=Decimal(0),
        )
    )
    db.commit()

    graph = build_graph(
        db=db,
        doc_intelligence=doc_intelligence,
        llm=MockInvoiceLLMClient(),
        blob=BlobStorageClient(),
        explainer=MockDecisionExplainerClient(),
        trace=True,
    )

    initial_state: GraphState = {
        "invoice_id": invoice_id,
        "file_hash": "",
        "is_scanned": False,
        "extracted": None,
        "field_confidence": {},
        "findings": [],
        "decision": None,
        "explanation": None,
        "supplier_email_draft": None,
        "pdf_bytes": pdf_bytes,
        "blob_url": "",
    }
    try:
        graph.invoke(initial_state)

        runs = db.scalars(
            select(AgentRun).where(AgentRun.invoice_id == invoice_id).order_by(AgentRun.started_at)
        ).all()

        assert [r.node for r in runs] == [
            "ingest",
            "extract",
            "validate",
            "match",
            "risk",
            "decide",
            "human_review",
        ]
        assert all(r.duration_ms >= 0 for r in runs)
        extract_run = next(r for r in runs if r.node == "extract")
        assert extract_run.output is not None
        assert extract_run.output["extracted"]["supplier_nit"] == "900482113"
    finally:
        db.execute(delete(AgentRun).where(AgentRun.invoice_id == invoice_id))
        db.execute(delete(Invoice).where(Invoice.id == invoice_id))
        db.commit()
