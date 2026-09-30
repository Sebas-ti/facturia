"""Only the two paths that resolve immediately (already done, not found) are
tested — the long-poll/timeout path would need the test to actually wait,
which isn't worth it here."""

from collections.abc import Generator
from datetime import UTC, datetime
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
    """Requires `docker compose up -d db` (see AGENTS.md)."""
    with SessionLocal() as session:
        yield session
        session.execute(delete(AgentRun))
        session.execute(delete(Invoice))
        session.commit()


def test_streams_progress_then_done_for_an_already_processed_invoice(db: Session) -> None:
    invoice = Invoice(
        id=uuid4(),
        file_hash="abc",
        blob_url="http://azurite/invoices/abc.pdf",
        status="PROCESSED",
        decision="APROBAR",
        invoice_number="FEPC-1",
        total=Decimal(100),
    )
    db.add(invoice)
    db.flush()
    db.add(
        AgentRun(
            invoice_id=invoice.id,
            node="ingest",
            started_at=datetime.now(UTC),
            duration_ms=10,
        )
    )
    db.commit()

    response = client.get(f"/api/invoices/{invoice.id}/events")

    assert response.status_code == 200
    assert "event: progress" in response.text
    assert '"node": "ingest"' in response.text
    assert "event: done" in response.text
    assert '"decision": "APROBAR"' in response.text


def test_streams_error_for_an_unknown_invoice() -> None:
    response = client.get(f"/api/invoices/{uuid4()}/events")

    assert response.status_code == 200
    assert "event: error" in response.text
