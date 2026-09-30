from decimal import Decimal

from sqlalchemy import select

from app.db.models import GoodsReceipt, PoLine, PurchaseOrder, Supplier
from app.db.session import SessionLocal
from scripts.seed import seed


def test_seed_loads_master_data_from_data_dir() -> None:
    """Requires `docker compose up -d db` and `alembic upgrade head` (see AGENTS.md)."""
    with SessionLocal() as db:
        seed(db)

        assert db.scalar(select(Supplier).where(Supplier.nit == "900482113")) is not None
        assert len(db.scalars(select(Supplier)).all()) == 6
        assert len(db.scalars(select(PurchaseOrder)).all()) == 11
        assert len(db.scalars(select(PoLine)).all()) == 24
        assert len(db.scalars(select(GoodsReceipt)).all()) == 24

        po_line = db.scalar(
            select(PoLine).join(PurchaseOrder).where(
                PurchaseOrder.number == "OC-2026-0101", PoLine.sku == "PAP-001"
            )
        )
        assert po_line is not None
        assert po_line.unit_price == Decimal(18500)


def test_seed_is_idempotent() -> None:
    with SessionLocal() as db:
        seed(db)
        seed(db)
        assert len(db.scalars(select(Supplier)).all()) == 6
