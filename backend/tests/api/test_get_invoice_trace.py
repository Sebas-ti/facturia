"""Tests for GET /api/invoices/{id}/trace (docs/spec.md §6)."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import AgentRun, Invoice
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    created_ids: list[str] = []
    with SessionLocal() as session:
        yield session
        if created_ids:
            session.execute(delete(AgentRun).where(AgentRun.invoice_id.in_(created_ids)))
            session.execute(delete(Invoice).where(Invoice.id.in_(created_ids)))
            session.commit()


def test_get_trace_not_found() -> None:
    random_id = uuid4()
    response = client.get(f"/api/invoices/{random_id}/trace")
    assert response.status_code == 404
    assert response.json()["detail"] == "Factura no encontrada"


def test_get_trace_empty_runs(db: Session) -> None:
    inv_id = uuid4()
    now = datetime.now(UTC)
    invoice = Invoice(
        id=inv_id,
        file_hash="hash_trace_empty",
        blob_url="http://azurite/invoices/trace_empty.pdf",
        status="PROCESSING",
        decision=None,
        invoice_number="PENDIENTE",
        total=Decimal(0),
        created_at=now,
        processed_ms=None,
    )
    db.add(invoice)
    db.commit()

    try:
        response = client.get(f"/api/invoices/{inv_id}/trace")
        assert response.status_code == 200
        data = response.json()
        assert data["invoice_id"] == str(inv_id)
        assert data["status"] == "PROCESSING"
        assert data["decision"] is None
        assert data["total_duration_ms"] == 0
        assert data["total_tokens_in"] == 0
        assert data["total_tokens_out"] == 0
        assert data["runs"] == []
    finally:
        db.execute(delete(Invoice).where(Invoice.id == inv_id))
        db.commit()


def test_get_trace_with_full_agent_runs(db: Session) -> None:
    inv_id = uuid4()
    base_time = datetime.now(UTC)

    invoice = Invoice(
        id=inv_id,
        file_hash="hash_trace_full",
        blob_url="http://azurite/invoices/trace_full.pdf",
        status="PROCESSED",
        decision="REVISION",
        invoice_number="FEPC-9999",
        total=Decimal("880600.00"),
        cost_usd=Decimal("0.0035"),
        created_at=base_time,
        processed_ms=1250,
    )
    db.add(invoice)

    nodes = [
        ("ingest", 120, None, None, {"file_hash": "abc", "is_scanned": False}),
        ("extract", 450, 850, 120, {"supplier_nit": "900482113"}),
        ("validate", 35, None, None, {"findings": []}),
        ("match", 60, None, None, {"status": "MATCH"}),
        ("risk", 45, None, None, {"findings": []}),
        ("decide", 380, 420, 95, {"decision": "REVISION"}),
        ("human_review", 15, None, None, {"status": "paused_for_review"}),
    ]

    for idx, (node_name, dur, tin, tout, out) in enumerate(nodes):
        run = AgentRun(
            id=uuid4(),
            invoice_id=inv_id,
            node=node_name,
            started_at=base_time + timedelta(seconds=idx),
            duration_ms=dur,
            tokens_in=tin,
            tokens_out=tout,
            output=out,
        )
        db.add(run)

    db.commit()

    try:
        response = client.get(f"/api/invoices/{inv_id}/trace")
        assert response.status_code == 200
        data = response.json()

        assert data["invoice_id"] == str(inv_id)
        assert data["status"] == "PROCESSED"
        assert data["decision"] == "REVISION"
        assert data["total_duration_ms"] == sum(n[1] for n in nodes)
        assert data["total_tokens_in"] == 850 + 420
        assert data["total_tokens_out"] == 120 + 95
        assert Decimal(str(data["cost_usd"])) == Decimal("0.0035")

        runs = data["runs"]
        assert len(runs) == 7
        assert [r["node"] for r in runs] == [n[0] for n in nodes]
        assert runs[1]["tokens_in"] == 850
        assert runs[1]["output"]["supplier_nit"] == "900482113"
        assert runs[6]["output"]["status"] == "paused_for_review"
    finally:
        db.execute(delete(AgentRun).where(AgentRun.invoice_id == inv_id))
        db.execute(delete(Invoice).where(Invoice.id == inv_id))
        db.commit()
