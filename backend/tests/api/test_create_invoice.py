"""Tests the POST /api/invoices endpoint's HTTP-layer behavior only — the
background task is monkeypatched to a no-op so these never call real Azure
(the endpoint always uses real clients, per PROGRESS.md 4.2's "siempre real"
decision; see tests/api/test_save_result.py for the persistence logic and
tests/test_graph.py for the real pipeline, both exercised without Azure)."""

from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

import app.api.invoices as invoices_module
from app.db.models import Invoice
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Requires `docker compose up -d db` (see AGENTS.md)."""
    with SessionLocal() as session:
        yield session
        session.execute(delete(Invoice).where(Invoice.invoice_number == "PENDIENTE"))
        session.commit()


@pytest.fixture(autouse=True)
def no_real_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(invoices_module, "_process_invoice", lambda *args, **kwargs: None)


def test_rejects_non_pdf_content_type() -> None:
    response = client.post(
        "/api/invoices", files={"file": ("factura.txt", b"hola", "text/plain")}
    )
    assert response.status_code == 422


def test_rejects_oversized_file() -> None:
    oversized = b"%PDF-1.4" + b"0" * invoices_module.MAX_UPLOAD_BYTES
    response = client.post(
        "/api/invoices", files={"file": ("factura.pdf", oversized, "application/pdf")}
    )
    assert response.status_code == 422


def test_accepts_a_pdf_and_creates_a_placeholder_invoice(db: Session) -> None:
    response = client.post(
        "/api/invoices", files={"file": ("factura.pdf", b"%PDF-1.4 fake", "application/pdf")}
    )

    assert response.status_code == 202
    invoice_id = UUID(response.json()["invoice_id"])

    invoice = db.scalars(select(Invoice).where(Invoice.id == invoice_id)).one()
    assert invoice.status == "PROCESSING"
    assert invoice.decision is None
