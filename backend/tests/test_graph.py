import hashlib
from collections.abc import Generator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from langgraph.types import Command
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.graph import GraphState, build_graph
from app.schemas.extraction import RawField, RawInvoiceExtraction, RawInvoiceLine
from app.schemas.finding import FindingCode
from app.services.blob import BlobStorageClient
from app.services.checkpoint import build_checkpointer
from app.services.doc_intelligence import FixtureDocumentIntelligenceClient
from app.services.explain import MockDecisionExplainerClient
from app.services.llm import MockInvoiceLLMClient
from scripts.seed import seed

DATA_DIR = Path(__file__).parents[2] / "data"


def _initial_state(pdf_bytes: bytes, invoice_id: UUID) -> GraphState:
    return {
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


def test_pipeline_end_to_end_approves_a_clean_invoice(db: Session) -> None:
    pdf_bytes = (DATA_DIR / "facturas" / "F01_FEPC-1045.pdf").read_bytes()
    file_hash = hashlib.sha256(pdf_bytes).hexdigest()
    doc_intelligence = FixtureDocumentIntelligenceClient({file_hash: _raw_f01()})

    graph = build_graph(
        db=db,
        doc_intelligence=doc_intelligence,
        llm=MockInvoiceLLMClient(),
        blob=BlobStorageClient(),
        explainer=MockDecisionExplainerClient(),
    )

    result = graph.invoke(_initial_state(pdf_bytes, uuid4()))

    assert result["file_hash"] == file_hash
    assert result["is_scanned"] is False
    assert result["blob_url"].endswith(f"{file_hash}.pdf")
    assert result["extracted"] is not None
    assert result["extracted"].supplier_nit == "900482113"
    assert result["findings"] == []
    assert result["decision"] == "APROBAR"
    assert result["supplier_email_draft"] is None
    assert "no presenta hallazgos" in (result["explanation"] or "")


def test_pipeline_end_to_end_rejects_an_unknown_supplier(db: Session) -> None:
    pdf_bytes = (DATA_DIR / "facturas" / "F01_FEPC-1045.pdf").read_bytes()
    file_hash = hashlib.sha256(pdf_bytes).hexdigest()
    raw = _raw_f01().model_copy(
        update={
            "supplier_nit": _field("999999999-1"),
            "supplier_name": _field("Proveedor Desconocido S.A.S."),
        }
    )
    doc_intelligence = FixtureDocumentIntelligenceClient({file_hash: raw})

    graph = build_graph(
        db=db,
        doc_intelligence=doc_intelligence,
        llm=MockInvoiceLLMClient(),
        blob=BlobStorageClient(),
        explainer=MockDecisionExplainerClient(),
    )

    result = graph.invoke(_initial_state(pdf_bytes, uuid4()))

    assert result["decision"] == "REVISION"
    assert FindingCode.UNKNOWN_SUPPLIER in [f.code for f in result["findings"]]


def test_human_in_the_loop_interrupt_and_resume(db: Session) -> None:
    """Requires `docker compose up -d db` (see AGENTS.md): uses the real
    Postgres checkpointer, not an in-memory one, to prove the pause actually
    persists and can be resumed from a separate `invoke` call — not just
    within the same one, which LangGraph also allows without a checkpointer.
    """
    pdf_bytes = (DATA_DIR / "facturas" / "F01_FEPC-1045.pdf").read_bytes()
    file_hash = hashlib.sha256(pdf_bytes).hexdigest()
    raw = _raw_f01().model_copy(update={"supplier_nit": _field("999999999-1")})
    doc_intelligence = FixtureDocumentIntelligenceClient({file_hash: raw})

    with build_checkpointer() as checkpointer:
        graph = build_graph(
            db=db,
            doc_intelligence=doc_intelligence,
            llm=MockInvoiceLLMClient(),
            blob=BlobStorageClient(),
            explainer=MockDecisionExplainerClient(),
            checkpointer=checkpointer,
        )
        invoice_id = uuid4()
        config = {"configurable": {"thread_id": str(invoice_id)}}

        paused = graph.invoke(_initial_state(pdf_bytes, invoice_id), config=config)
        assert paused.get("__interrupt__")
        assert paused["decision"] == "REVISION"

        resumed = graph.invoke(Command(resume="APROBAR"), config=config)

    assert resumed["decision"] == "APROBAR"
    assert not resumed.get("__interrupt__")
    assert resumed["extracted"] is not None  # state from before the pause survives
