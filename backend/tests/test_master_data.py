from collections.abc import Generator
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Invoice, Supplier
from app.db.session import SessionLocal
from app.services.master_data import (
    load_previous_file_hashes,
    load_previous_invoice_numbers,
    load_previously_invoiced_quantity,
    load_purchase_orders,
    load_received_quantity,
    load_suppliers,
)
from scripts.seed import seed

_TEST_FILE_HASH_PREFIX = "test-master-data-"


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Requires `docker compose up -d db` and `alembic upgrade head` (see AGENTS.md)."""
    with SessionLocal() as session:
        seed(session)
        yield session
        session.execute(
            delete(Invoice).where(Invoice.file_hash.like(f"{_TEST_FILE_HASH_PREFIX}%"))
        )
        session.commit()


@pytest.fixture
def condor_supplier_id(db: Session) -> UUID:
    return db.scalars(select(Supplier.id).where(Supplier.nit == "900482113")).one()


def _insert_invoice(
    db: Session,
    *,
    suffix: str,
    supplier_id: UUID,
    invoice_number: str,
    decision: str | None,
    purchase_order: str | None,
    lines: list[dict[str, object]],
) -> Invoice:
    invoice = Invoice(
        file_hash=f"{_TEST_FILE_HASH_PREFIX}{suffix}",
        blob_url="http://example.invalid/fake.pdf",
        status="PROCESSED",
        decision=decision,
        supplier_id=supplier_id,
        invoice_number=invoice_number,
        total=Decimal(1000),
        extracted={"purchase_order": purchase_order, "lines": lines},
    )
    db.add(invoice)
    db.flush()
    return invoice


def test_load_purchase_orders_matches_seeded_data(db: Session) -> None:
    orders = load_purchase_orders(db)
    assert "OC-2026-0101" in orders
    po = orders["OC-2026-0101"]
    assert po.supplier_nit == "900482113"
    line = next(line for line in po.lines if line.sku == "PAP-001")
    assert line.quantity == Decimal(40)
    assert line.unit_price == Decimal(18500)


def test_load_received_quantity_matches_seeded_data(db: Session) -> None:
    received = load_received_quantity(db)
    assert received[("OC-2026-0101", "PAP-001")] == Decimal(40)


def test_load_suppliers_matches_seeded_data(db: Session) -> None:
    suppliers = load_suppliers(db)
    supplier = suppliers["900482113"]
    assert supplier.name == "Papelería El Cóndor S.A.S."
    assert supplier.status == "ACTIVO"
    assert supplier.bank_account.bank == "Bancolombia"


def test_load_previously_invoiced_quantity_accumulates_non_rejected_invoices(
    db: Session, condor_supplier_id: UUID
) -> None:
    _insert_invoice(
        db,
        suffix="a",
        supplier_id=condor_supplier_id,
        invoice_number="TEST-A",
        decision="APROBAR",
        purchase_order="OC-2026-0101",
        lines=[{"sku": "PAP-001", "quantity": 5}],
    )
    _insert_invoice(
        db,
        suffix="b",
        supplier_id=condor_supplier_id,
        invoice_number="TEST-B",
        decision="RECHAZAR",
        purchase_order="OC-2026-0101",
        lines=[{"sku": "PAP-001", "quantity": 100}],
    )
    db.commit()

    accumulated = load_previously_invoiced_quantity(db)

    assert accumulated[("OC-2026-0101", "PAP-001")] == Decimal(5)


def test_load_previous_invoice_numbers_and_file_hashes(
    db: Session, condor_supplier_id: UUID
) -> None:
    invoice = _insert_invoice(
        db,
        suffix="c",
        supplier_id=condor_supplier_id,
        invoice_number="TEST-C",
        decision="APROBAR",
        purchase_order=None,
        lines=[],
    )
    db.commit()

    assert ("900482113", "TEST-C") in load_previous_invoice_numbers(db)
    assert f"{_TEST_FILE_HASH_PREFIX}c" in load_previous_file_hashes(db)

    assert ("900482113", "TEST-C") not in load_previous_invoice_numbers(
        db, exclude_invoice_id=invoice.id
    )
