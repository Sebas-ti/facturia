"""Tests for GET /api/invoices/{id} and GET /api/invoices/{id}/file (docs/spec.md §6)."""

from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import AgentRun, FindingRecord, Invoice, Supplier
from app.db.session import SessionLocal
from app.main import app
from app.schemas.finding import FindingCode
from app.services.blob import BlobStorageClient
from scripts.seed import seed

client = TestClient(app)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Ensures test database has seed master data and cleans up test invoices."""
    created_ids: list[str] = []
    with SessionLocal() as session:
        seed(session)
        yield session
        if created_ids:
            session.execute(delete(FindingRecord).where(FindingRecord.invoice_id.in_(created_ids)))
            session.execute(delete(AgentRun).where(AgentRun.invoice_id.in_(created_ids)))
            session.execute(delete(Invoice).where(Invoice.id.in_(created_ids)))
            session.commit()


def test_get_invoice_not_found() -> None:
    random_id = uuid4()
    response = client.get(f"/api/invoices/{random_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Factura no encontrada"


def test_get_invoice_detail_with_three_way_match(db: Session) -> None:
    supplier = db.query(Supplier).filter(Supplier.nit == "900482113").first()
    assert supplier is not None

    inv_id = uuid4()
    now = datetime.now(UTC)

    invoice = Invoice(
        id=inv_id,
        file_hash="hash_detail_test",
        blob_url="http://azurite/invoices/hash_detail_test.pdf",
        status="PROCESSED",
        decision="REVISION",
        supplier_id=supplier.id,
        invoice_number="FEPC-5001",
        total=Decimal("1425620.00"),
        created_at=now,
        extracted={
            "supplier_nit": "900482113",
            "supplier_name": "Papelería El Cóndor S.A.S.",
            "invoice_number": "FEPC-5001",
            "issue_date": "2026-09-10",
            "due_date": "2026-10-10",
            "purchase_order": "OC-2026-0101",
            "currency": "COP",
            "subtotal": "1198000.00",
            "vat_total": "227620.00",
            "total": "1425620.00",
            "cufe": "a" * 96,
            "bank_account": {
                "bank": "Bancolombia",
                "account_type": "Corriente",
                "number": "98765432109",
            },
            "lines": [
                {
                    "sku": "PAP-001",
                    "description": "Resma de papel carta 75g",
                    "quantity": "40",
                    "unit_price": "29950.00",
                    "vat_rate": "19.0",
                    "line_subtotal": "1198000.00",
                }
            ],
        },
    )

    finding = FindingRecord(
        id=uuid4(),
        invoice_id=inv_id,
        code=FindingCode.BANK_ACCOUNT_CHANGED.value,
        severity="CRITICA",
        message="Cuenta modificada",
        evidence={"esperada": "123", "encontrada": "98765432109"},
    )

    run_extract = AgentRun(
        id=uuid4(),
        invoice_id=inv_id,
        node="extract",
        started_at=now,
        duration_ms=450,
        output={"field_confidence": {"supplier_nit": 0.99, "total": 0.95}},
    )

    run_decide = AgentRun(
        id=uuid4(),
        invoice_id=inv_id,
        node="decide",
        started_at=now,
        duration_ms=300,
        output={
            "decision": "REVISION",
            "explanation": "Se requiere revisión por posible cambio de cuenta bancaria.",
            "supplier_email_draft": None,
        },
    )

    db.add_all([invoice, finding, run_extract, run_decide])
    db.commit()

    try:
        response = client.get(f"/api/invoices/{inv_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(inv_id)
        assert data["invoice_number"] == "FEPC-5001"
        assert data["supplier_name"] == "Papelería El Cóndor S.A.S."
        assert data["has_bank_account_alert"] is True
        assert data["field_confidence"]["supplier_nit"] == 0.99
        assert data["explanation"] == "Se requiere revisión por posible cambio de cuenta bancaria."

        # Three way match verification with OC-2026-001 from seed
        assert len(data["three_way_match"]) == 1
        line_match = data["three_way_match"][0]
        assert line_match["sku"] == "PAP-001"
        assert line_match["po_unit_price"] is not None
        assert line_match["received_qty"] is not None

        # Purchase order summary
        assert data["purchase_order"] is not None
        assert data["purchase_order"]["number"] == "OC-2026-0101"

    finally:
        db.execute(delete(FindingRecord).where(FindingRecord.invoice_id == inv_id))
        db.execute(delete(AgentRun).where(AgentRun.invoice_id == inv_id))
        db.execute(delete(Invoice).where(Invoice.id == inv_id))
        db.commit()


def test_get_invoice_file_sas(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    inv_id = uuid4()
    invoice = Invoice(
        id=inv_id,
        file_hash="test_sas_hash",
        blob_url="http://azurite/invoices/test_sas_hash.pdf",
        status="PROCESSED",
        invoice_number="FEPC-9999",
        total=Decimal("100.00"),
    )
    db.add(invoice)
    db.commit()

    monkeypatch.setattr(
        BlobStorageClient,
        "generate_sas_url",
        lambda self, file_hash, expiry_hours=1: f"http://azurite/invoices/{file_hash}.pdf?sig=mocked_sas",
    )

    try:
        response = client.get(f"/api/invoices/{inv_id}/file")
        assert response.status_code == 200
        data = response.json()
        assert "mocked_sas" in data["url"]
        assert data["file_hash"] == "test_sas_hash"
        assert data["expires_in_seconds"] == 3600
    finally:
        db.execute(delete(Invoice).where(Invoice.id == inv_id))
        db.commit()


def test_get_invoice_file_stream(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    inv_id = uuid4()
    invoice = Invoice(
        id=inv_id,
        file_hash="test_stream_hash",
        blob_url="http://azurite/invoices/test_stream_hash.pdf",
        status="PROCESSED",
        invoice_number="FEPC-STREAM",
        total=Decimal("100.00"),
    )
    db.add(invoice)
    db.commit()

    monkeypatch.setattr(
        BlobStorageClient,
        "download_pdf",
        lambda self, file_hash: b"%PDF-1.4 mock binary pdf stream",
    )

    try:
        response = client.get(f"/api/invoices/{inv_id}/file?stream=true")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert b"%PDF-1.4 mock binary pdf stream" in response.content
    finally:
        db.execute(delete(Invoice).where(Invoice.id == inv_id))
        db.commit()
