from collections.abc import Generator
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.invoices import _save_result
from app.db.models import AgentRun, FindingRecord, Invoice, Supplier
from app.db.session import SessionLocal
from app.schemas.finding import Finding, FindingCode
from app.schemas.invoice import ExtractedInvoice
from scripts.seed import seed


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Requires `docker compose up -d db` and `alembic upgrade head` (see AGENTS.md).

    Cleans up every Invoice this file creates: Invoice.supplier_id is a real
    FK, so a leftover row blocks `seed()`'s `delete(Supplier)` for any test
    that runs after this one (see PROGRESS.md 3.10 for the same bug elsewhere).
    """
    with SessionLocal() as session:
        seed(session)
        yield session
        session.execute(delete(FindingRecord))
        session.execute(delete(AgentRun))
        session.execute(delete(Invoice))
        session.commit()


def _placeholder_invoice(db: Session) -> Invoice:
    invoice = Invoice(
        id=uuid4(),
        file_hash="pending",
        blob_url="pending",
        status="PROCESSING",
        invoice_number="PENDIENTE",
        total=Decimal(0),
    )
    db.add(invoice)
    db.commit()
    return invoice


def _extracted_invoice() -> ExtractedInvoice:
    return ExtractedInvoice(
        supplier_nit="900482113",
        supplier_dv=6,
        supplier_name="Papelería El Cóndor S.A.S.",
        invoice_number="FEPC-9999",
        issue_date=date(2026, 9, 1),
        due_date=None,
        purchase_order=None,
        lines=[],
        subtotal=Decimal(1000),
        vat_total=Decimal(190),
        total=Decimal(1190),
        cufe=None,
        bank_account=None,
    )


def test_save_result_updates_the_invoice_and_resolves_the_supplier(db: Session) -> None:
    placeholder = _placeholder_invoice(db)
    extracted = _extracted_invoice()
    result: dict[str, Any] = {
        "file_hash": "abc123",
        "blob_url": "http://azurite/invoices/abc123.pdf",
        "decision": "APROBAR",
        "extracted": extracted,
        "findings": [],
    }

    _save_result(db, placeholder.id, result)

    invoice = db.scalars(select(Invoice).where(Invoice.id == placeholder.id)).one()
    assert invoice.status == "PROCESSED"
    assert invoice.decision == "APROBAR"
    assert invoice.invoice_number == "FEPC-9999"
    assert invoice.total == Decimal(1190)
    assert invoice.file_hash == "abc123"

    supplier = db.scalars(select(Supplier).where(Supplier.id == invoice.supplier_id)).one()
    assert supplier.nit == "900482113"


def test_save_result_persists_findings(db: Session) -> None:
    placeholder = _placeholder_invoice(db)
    finding = Finding(
        code=FindingCode.MISSING_PO, severity="MEDIA", message="sin OC", evidence={}
    )
    result: dict[str, Any] = {
        "file_hash": "def456",
        "blob_url": "http://azurite/invoices/def456.pdf",
        "decision": "REVISION",
        "extracted": _extracted_invoice(),
        "findings": [finding],
    }

    _save_result(db, placeholder.id, result)

    records = db.scalars(
        select(FindingRecord).where(FindingRecord.invoice_id == placeholder.id)
    ).all()
    assert [r.code for r in records] == ["MISSING_PO"]


def test_save_result_handles_unknown_supplier(db: Session) -> None:
    placeholder = _placeholder_invoice(db)
    extracted = _extracted_invoice().model_copy(update={"supplier_nit": "999999999"})
    result: dict[str, Any] = {
        "file_hash": "ghi789",
        "blob_url": "http://azurite/invoices/ghi789.pdf",
        "decision": "REVISION",
        "extracted": extracted,
        "findings": [],
    }

    _save_result(db, placeholder.id, result)

    invoice = db.scalars(select(Invoice).where(Invoice.id == placeholder.id)).one()
    assert invoice.supplier_id is None


def test_save_result_handles_missing_extraction(db: Session) -> None:
    placeholder = _placeholder_invoice(db)
    result: dict[str, Any] = {
        "file_hash": "jkl012",
        "blob_url": "http://azurite/invoices/jkl012.pdf",
        "decision": "REVISION",
        "extracted": None,
        "findings": [],
    }

    _save_result(db, placeholder.id, result)

    invoice = db.scalars(select(Invoice).where(Invoice.id == placeholder.id)).one()
    assert invoice.invoice_number == "DESCONOCIDO"
    assert invoice.total == Decimal(0)
    assert invoice.extracted is None
