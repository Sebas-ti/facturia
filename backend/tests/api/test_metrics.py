"""Tests for GET /api/metrics endpoint (docs/spec.md §7)."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.models import AgentRun, FindingRecord, Invoice, Review, Supplier
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


@pytest.fixture
def managed_invoices() -> Generator[list[UUID], None, None]:
    created_ids: list[UUID] = []
    yield created_ids
    with SessionLocal() as session:
        if created_ids:
            session.execute(delete(Review).where(Review.invoice_id.in_(created_ids)))
            session.execute(delete(AgentRun).where(AgentRun.invoice_id.in_(created_ids)))
            session.execute(delete(FindingRecord).where(FindingRecord.invoice_id.in_(created_ids)))
            session.execute(delete(Invoice).where(Invoice.id.in_(created_ids)))
            session.commit()


def test_get_metrics_response_structure() -> None:
    response = client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()

    assert "kpis" in data
    assert "decisions_summary" in data
    assert "daily_decisions" in data
    assert "top_findings" in data

    kpis = data["kpis"]
    assert "total_invoices" in kpis
    assert "processed_invoices" in kpis
    assert "auto_approved_count" in kpis
    assert "auto_approval_rate_pct" in kpis
    assert "avg_processing_time_ms" in kpis
    assert "total_processing_time_ms" in kpis
    assert "estimated_hours_saved" in kpis
    assert "total_ai_cost_usd" in kpis


def test_get_metrics_calculations(managed_invoices: list[UUID]) -> None:
    with SessionLocal() as db:
        supplier = db.query(Supplier).first()
        supplier_id = supplier.id if supplier else None

        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)

        # 1. Auto-approved invoice (no review)
        inv1_id = uuid4()
        inv1 = Invoice(
            id=inv1_id,
            file_hash="hash_m1",
            blob_url="https://blob/m1",
            status="PROCESSED",
            decision="APROBAR",
            supplier_id=supplier_id,
            invoice_number="FAC-M1",
            total=Decimal("150000.00"),
            processed_ms=1200,
            cost_usd=Decimal("0.0125"),
            created_at=yesterday,
        )

        # 2. Human-reviewed approved invoice (has a Review entry)
        inv2_id = uuid4()
        inv2 = Invoice(
            id=inv2_id,
            file_hash="hash_m2",
            blob_url="https://blob/m2",
            status="PROCESSED",
            decision="APROBAR",
            supplier_id=supplier_id,
            invoice_number="FAC-M2",
            total=Decimal("250000.00"),
            processed_ms=2400,
            cost_usd=Decimal("0.0150"),
            created_at=now,
        )
        rev2 = Review(
            invoice_id=inv2_id,
            action="APROBAR",
            reviewer="analista@empresa.com",
            comment="Aprobado tras justificación",
            created_at=now,
        )

        # 3. In-review invoice with 2 findings
        inv3_id = uuid4()
        inv3 = Invoice(
            id=inv3_id,
            file_hash="hash_m3",
            blob_url="https://blob/m3",
            status="PROCESSED",
            decision="REVISION",
            supplier_id=supplier_id,
            invoice_number="FAC-M3",
            total=Decimal("350000.00"),
            processed_ms=1800,
            cost_usd=Decimal("0.0110"),
            created_at=now,
        )
        f1 = FindingRecord(
            invoice_id=inv3_id,
            code="BANK_ACCOUNT_CHANGED",
            severity="CRITICA",
            message="Cambio no registrado de cuenta bancaria",
            evidence={},
        )
        f2 = FindingRecord(
            invoice_id=inv3_id,
            code="PRICE_MISMATCH",
            severity="MEDIA",
            message="Discrepancia en precio unitario",
            evidence={},
        )

        # 4. Rejected invoice with 1 finding
        inv4_id = uuid4()
        inv4 = Invoice(
            id=inv4_id,
            file_hash="hash_m4",
            blob_url="https://blob/m4",
            status="PROCESSED",
            decision="RECHAZAR",
            supplier_id=supplier_id,
            invoice_number="FAC-M4",
            total=Decimal("450000.00"),
            processed_ms=1000,
            cost_usd=Decimal("0.0105"),
            created_at=now,
        )
        f3 = FindingRecord(
            invoice_id=inv4_id,
            code="ARITHMETIC_ERROR",
            severity="ALTA",
            message="Error en suma de subtotales",
            evidence={},
        )

        # 5. Pending / in-process invoice
        inv5_id = uuid4()
        inv5 = Invoice(
            id=inv5_id,
            file_hash="hash_m5",
            blob_url="https://blob/m5",
            status="PROCESSING",
            decision=None,
            supplier_id=supplier_id,
            invoice_number="PENDIENTE",
            total=Decimal("0.00"),
            created_at=now,
        )

        db.add_all([inv1, inv2, inv3, inv4, inv5, rev2, f1, f2, f3])
        db.commit()

        managed_invoices.extend([inv1_id, inv2_id, inv3_id, inv4_id, inv5_id])

    response = client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()

    kpis = data["kpis"]
    assert kpis["total_invoices"] >= 5
    assert kpis["processed_invoices"] >= 4
    # inv1 is auto-approved; inv2 was approved by human review
    assert kpis["auto_approved_count"] >= 1
    assert kpis["auto_approval_rate_pct"] > 0
    assert kpis["avg_processing_time_ms"] > 0
    assert kpis["total_processing_time_ms"] > 0
    assert kpis["estimated_hours_saved"] >= 0.5
    assert Decimal(str(kpis["total_ai_cost_usd"])) > Decimal("0.04")

    # Decisions breakdown
    summary = data["decisions_summary"]
    assert summary["aprobar"] >= 2
    assert summary["revision"] >= 1
    assert summary["rechazar"] >= 1
    assert summary["pending"] >= 1

    # Daily decisions
    daily = data["daily_decisions"]
    assert len(daily) >= 1
    today_str = now.date().isoformat()
    today_point = next((p for p in daily if p["date"] == today_str), None)
    assert today_point is not None
    assert today_point["total"] >= 4

    # Top findings
    top_findings = data["top_findings"]
    assert len(top_findings) >= 3
    finding_codes = [f["code"] for f in top_findings]
    assert "BANK_ACCOUNT_CHANGED" in finding_codes
    assert "PRICE_MISMATCH" in finding_codes
    assert "ARITHMETIC_ERROR" in finding_codes

    bank_finding = next(f for f in top_findings if f["code"] == "BANK_ACCOUNT_CHANGED")
    assert bank_finding["label"] == "Cambio no autorizado de cuenta bancaria"
    assert bank_finding["severity"] == "CRITICA"
    assert bank_finding["count"] >= 1
    assert bank_finding["percentage"] > 0
