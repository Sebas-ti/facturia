"""Tests for POST /api/invoices/{id}/review (docs/spec.md §6)."""

from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import AgentRun, Invoice, Review
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    created_ids: list[str] = []
    with SessionLocal() as session:
        yield session
        if created_ids:
            session.execute(delete(Review).where(Review.invoice_id.in_(created_ids)))
            session.execute(delete(AgentRun).where(AgentRun.invoice_id.in_(created_ids)))
            session.execute(delete(Invoice).where(Invoice.id.in_(created_ids)))
            session.commit()


def test_review_invoice_not_found() -> None:
    random_id = uuid4()
    response = client.post(
        f"/api/invoices/{random_id}/review",
        json={"action": "APROBAR", "comment": "Todo ok"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Factura no encontrada"


def test_review_invoice_not_in_revision_returns_400(db: Session) -> None:
    inv_id = uuid4()
    now = datetime.now(UTC)
    invoice = Invoice(
        id=inv_id,
        file_hash="hash_already_approved",
        blob_url="http://azurite/invoices/already_approved.pdf",
        status="PROCESSED",
        decision="APROBAR",
        invoice_number="FEPC-1001",
        total=Decimal("500000.00"),
        created_at=now,
    )
    db.add(invoice)
    db.commit()

    try:
        response = client.post(
            f"/api/invoices/{inv_id}/review",
            json={"action": "RECHAZAR", "comment": "Intento de cambio inválido"},
        )
        assert response.status_code == 400
        assert "Solo facturas en REVISION" in response.json()["detail"]
    finally:
        db.execute(delete(Invoice).where(Invoice.id == inv_id))
        db.commit()


def test_review_invoice_invalid_action(db: Session) -> None:
    inv_id = uuid4()
    invoice = Invoice(
        id=inv_id,
        file_hash="hash_invalid_act",
        blob_url="http://azurite/invoices/inv_act.pdf",
        status="PROCESSED",
        decision="REVISION",
        invoice_number="FEPC-1002",
        total=Decimal("500000.00"),
        created_at=datetime.now(UTC),
    )
    db.add(invoice)
    db.commit()

    try:
        response = client.post(
            f"/api/invoices/{inv_id}/review",
            json={"action": "IGNORAR", "comment": "Acción inválida"},
        )
        assert response.status_code == 422
    finally:
        db.execute(delete(Invoice).where(Invoice.id == inv_id))
        db.commit()


def test_review_invoice_approves_and_persists_review(db: Session) -> None:
    inv_id = uuid4()
    now = datetime.now(UTC)
    invoice = Invoice(
        id=inv_id,
        file_hash="hash_rev_approve",
        blob_url="http://azurite/invoices/rev_approve.pdf",
        status="PROCESSED",
        decision="REVISION",
        invoice_number="FEPC-7777",
        total=Decimal("1500000.00"),
        created_at=now,
    )
    db.add(invoice)
    db.commit()

    try:
        payload = {
            "action": "APROBAR",
            "comment": "Precio autorizado excepcionalmente por gerencia.",
            "reviewer": "analyst.senior@facturia.local",
        }
        response = client.post(f"/api/invoices/{inv_id}/review", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["invoice_id"] == str(inv_id)
        assert data["action"] == "APROBAR"
        assert data["previous_decision"] == "REVISION"
        assert data["new_decision"] == "APROBAR"
        assert data["comment"] == "Precio autorizado excepcionalmente por gerencia."
        assert data["reviewer"] == "analyst.senior@facturia.local"

        # Verify DB invoice updated
        db.expire_all()
        updated_invoice = db.get(Invoice, inv_id)
        assert updated_invoice is not None
        assert updated_invoice.decision == "APROBAR"

        # Verify DB review record created
        review_record = db.query(Review).filter(Review.invoice_id == inv_id).first()
        assert review_record is not None
        assert review_record.action == "APROBAR"
        assert review_record.reviewer == "analyst.senior@facturia.local"
        assert review_record.comment == "Precio autorizado excepcionalmente por gerencia."
    finally:
        db.execute(delete(Review).where(Review.invoice_id == inv_id))
        db.execute(delete(Invoice).where(Invoice.id == inv_id))
        db.commit()


def test_review_invoice_rejects_and_persists_review(db: Session) -> None:
    inv_id = uuid4()
    now = datetime.now(UTC)
    invoice = Invoice(
        id=inv_id,
        file_hash="hash_rev_reject",
        blob_url="http://azurite/invoices/rev_reject.pdf",
        status="PROCESSED",
        decision="REVISION",
        invoice_number="FEPC-8888",
        total=Decimal("2500000.00"),
        created_at=now,
    )
    db.add(invoice)
    db.commit()

    try:
        payload = {
            "action": "RECHAZAR",
            "comment": "Rechazado: Proveedor no suministró nota crédito solicitada.",
            "reviewer": "auditor@facturia.local",
        }
        response = client.post(f"/api/invoices/{inv_id}/review", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["invoice_id"] == str(inv_id)
        assert data["action"] == "RECHAZAR"
        assert data["previous_decision"] == "REVISION"
        assert data["new_decision"] == "RECHAZAR"
        assert data["comment"] == "Rechazado: Proveedor no suministró nota crédito solicitada."

        db.expire_all()
        updated_invoice = db.get(Invoice, inv_id)
        assert updated_invoice is not None
        assert updated_invoice.decision == "RECHAZAR"
    finally:
        db.execute(delete(Review).where(Review.invoice_id == inv_id))
        db.execute(delete(Invoice).where(Invoice.id == inv_id))
        db.commit()


def test_review_invoice_calls_resume_graph(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    inv_id = uuid4()
    now = datetime.now(UTC)
    invoice = Invoice(
        id=inv_id,
        file_hash="hash_rev_mock",
        blob_url="http://azurite/invoices/rev_mock.pdf",
        status="PROCESSED",
        decision="REVISION",
        invoice_number="FEPC-5555",
        total=Decimal("1000000.00"),
        created_at=now,
    )
    db.add(invoice)
    db.commit()

    called: list[tuple[UUID, str]] = []

    def fake_resume(i_id: UUID, act: str) -> None:
        called.append((i_id, act))

    monkeypatch.setattr("app.api.invoices._resume_graph", fake_resume)

    try:
        response = client.post(
            f"/api/invoices/{inv_id}/review",
            json={"action": "APROBAR", "comment": "Aprobado", "reviewer": "admin"},
        )
        assert response.status_code == 200
        assert len(called) == 1
        assert called[0] == (inv_id, "APROBAR")
    finally:
        db.execute(delete(Review).where(Review.invoice_id == inv_id))
        db.execute(delete(Invoice).where(Invoice.id == inv_id))
        db.commit()

