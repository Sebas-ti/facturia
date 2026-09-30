"""Tests for GET /api/invoices endpoint (docs/spec.md §6)."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import FindingRecord, Invoice, Supplier
from app.db.session import SessionLocal
from app.main import app
from app.schemas.finding import FindingCode

client = TestClient(app)


@pytest.fixture
def clean_invoices() -> Generator[Session, None, None]:
    """Ensures test invoices and findings created during the tests are wiped."""
    created_ids: list[str] = []
    with SessionLocal() as session:
        yield session
        if created_ids:
            session.execute(delete(FindingRecord).where(FindingRecord.invoice_id.in_(created_ids)))
            session.execute(delete(Invoice).where(Invoice.id.in_(created_ids)))
            session.commit()


def test_list_invoices_empty_response() -> None:
    response = client.get("/api/invoices?status=NON_EXISTENT")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total_pages"] == 1


def test_list_invoices_filters_and_pagination(clean_invoices: Session) -> None:
    db = clean_invoices
    supplier = db.query(Supplier).first()
    supplier_id = supplier.id if supplier else None

    inv1_id = uuid4()
    inv2_id = uuid4()
    inv3_id = uuid4()

    now = datetime.now(UTC)
    inv1 = Invoice(
        id=inv1_id,
        file_hash="hash_1",
        blob_url="https://blob/1",
        status="PROCESSED",
        decision="APROBAR",
        supplier_id=supplier_id,
        invoice_number="TEST-001",
        total=Decimal("150000.00"),
        created_at=now - timedelta(minutes=5),
        extracted={"supplier_name": "Test Supplier", "supplier_nit": "900123456", "issue_date": "2026-09-01"},
    )
    inv2 = Invoice(
        id=inv2_id,
        file_hash="hash_2",
        blob_url="https://blob/2",
        status="PROCESSED",
        decision="REVISION",
        supplier_id=supplier_id,
        invoice_number="TEST-002",
        total=Decimal("300000.00"),
        created_at=now - timedelta(minutes=2),
        extracted={"supplier_name": "Test Supplier", "supplier_nit": "900123456", "issue_date": "2026-09-02"},
    )
    inv3 = Invoice(
        id=inv3_id,
        file_hash="hash_3",
        blob_url="https://blob/3",
        status="PROCESSING",
        decision=None,
        supplier_id=None,
        invoice_number="PENDIENTE",
        total=Decimal("0.00"),
        created_at=now,
    )
    db.add_all([inv1, inv2, inv3])
    db.commit()

    try:
        # Filter by decision
        res_decision = client.get("/api/invoices?decision=APROBAR&search=TEST-001")
        assert res_decision.status_code == 200
        data_decision = res_decision.json()
        assert data_decision["total"] == 1
        assert data_decision["items"][0]["invoice_number"] == "TEST-001"
        assert data_decision["items"][0]["decision"] == "APROBAR"

        # Filter by status
        res_status = client.get("/api/invoices?status=PROCESSING&search=PENDIENTE")
        assert res_status.status_code == 200
        data_status = res_status.json()
        assert any(item["id"] == str(inv3_id) for item in data_status["items"])

        # Pagination
        res_page1 = client.get("/api/invoices?page=1&page_size=2")
        assert res_page1.status_code == 200
        data_p1 = res_page1.json()
        assert len(data_p1["items"]) <= 2
        assert data_p1["page"] == 1
        assert data_p1["page_size"] == 2
    finally:
        db.execute(delete(Invoice).where(Invoice.id.in_([inv1_id, inv2_id, inv3_id])))
        db.commit()


def test_list_invoices_bank_account_alert_order_and_filter(clean_invoices: Session) -> None:
    db = clean_invoices

    inv_normal_id = uuid4()
    inv_alert_id = uuid4()

    now = datetime.now(UTC)
    # inv_normal was created MORE RECENTLY than inv_alert
    inv_normal = Invoice(
        id=inv_normal_id,
        file_hash="hash_normal",
        blob_url="https://blob/normal",
        status="PROCESSED",
        decision="APROBAR",
        invoice_number="NORM-999",
        total=Decimal("100000.00"),
        created_at=now,
    )
    inv_alert = Invoice(
        id=inv_alert_id,
        file_hash="hash_alert",
        blob_url="https://blob/alert",
        status="PROCESSED",
        decision="REVISION",
        invoice_number="ALRT-999",
        total=Decimal("200000.00"),
        created_at=now - timedelta(hours=1),
    )
    finding_alert = FindingRecord(
        id=uuid4(),
        invoice_id=inv_alert_id,
        code=FindingCode.BANK_ACCOUNT_CHANGED.value,
        severity="CRITICA",
        message="La cuenta bancaria cambió.",
        evidence={"esperada": "123", "encontrada": "456"},
    )

    db.add_all([inv_normal, inv_alert, finding_alert])
    db.commit()

    try:
        # Check ordering: search for both invoices
        res = client.get("/api/invoices?search=999")
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 2
        # ALRT-999 must come first because of BANK_ACCOUNT_CHANGED, despite being older!
        assert items[0]["invoice_number"] == "ALRT-999"
        assert items[0]["has_bank_account_alert"] is True
        assert items[1]["invoice_number"] == "NORM-999"
        assert items[1]["has_bank_account_alert"] is False

        # Check bank_account_alert=true filter
        res_alert_only = client.get("/api/invoices?bank_account_alert=true&search=999")
        assert res_alert_only.status_code == 200
        alert_items = res_alert_only.json()["items"]
        assert len(alert_items) == 1
        assert alert_items[0]["invoice_number"] == "ALRT-999"
    finally:
        db.execute(delete(FindingRecord).where(FindingRecord.invoice_id.in_([inv_normal_id, inv_alert_id])))
        db.execute(delete(Invoice).where(Invoice.id.in_([inv_normal_id, inv_alert_id])))
        db.commit()
