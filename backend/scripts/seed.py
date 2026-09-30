"""Load data/{proveedores.csv, ordenes_compra.json, recepciones.csv} into Postgres.

Idempotent: clears existing master data (goods_receipts -> po_lines ->
purchase_orders -> suppliers) before reinserting, so it's safe to rerun.
Doesn't touch invoices/findings/agent_runs/reviews (those come from the
processing pipeline, not the master data seed).
"""

import csv
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import GoodsReceipt, PoLine, PurchaseOrder, Supplier
from app.db.session import SessionLocal

DATA_DIR = Path(__file__).parents[2] / "data"


def _load_suppliers(db: Session) -> dict[str, Supplier]:
    suppliers: dict[str, Supplier] = {}
    with (DATA_DIR / "proveedores.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            supplier = Supplier(
                nit=row["nit"],
                dv=int(row["dv"]),
                name=row["razon_social"],
                email=row["email"],
                bank=row["banco"],
                account_type=row["tipo_cuenta"],
                account_number=row["cuenta"],
                status=row["estado"],
            )
            db.add(supplier)
            suppliers[row["nit"]] = supplier
    db.flush()
    return suppliers


def _load_purchase_orders(
    db: Session, suppliers: dict[str, Supplier]
) -> dict[tuple[str, str], PoLine]:
    raw = json.loads((DATA_DIR / "ordenes_compra.json").read_text(encoding="utf-8"))
    po_lines_by_key: dict[tuple[str, str], PoLine] = {}

    for oc in raw:
        po = PurchaseOrder(
            number=oc["numero"],
            supplier=suppliers[oc["proveedor_nit"]],
            date=date.fromisoformat(oc["fecha"]),
            status=oc["estado"],
        )
        db.add(po)
        for linea in oc["lineas"]:
            po_line = PoLine(
                purchase_order=po,
                sku=linea["sku"],
                description=linea["descripcion"],
                quantity=Decimal(str(linea["cantidad"])),
                unit_price=Decimal(str(linea["precio_unitario"])),
                vat_rate=Decimal(str(linea["iva_pct"])),
            )
            db.add(po_line)
            po_lines_by_key[(oc["numero"], linea["sku"])] = po_line

    db.flush()
    return po_lines_by_key


def _load_goods_receipts(db: Session, po_lines_by_key: dict[tuple[str, str], PoLine]) -> None:
    with (DATA_DIR / "recepciones.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["orden_compra"], row["sku"])
            received_at = datetime.combine(
                date.fromisoformat(row["fecha_recepcion"]), datetime.min.time(), tzinfo=UTC
            )
            db.add(
                GoodsReceipt(
                    po_line=po_lines_by_key[key],
                    quantity_received=Decimal(row["cantidad_recibida"]),
                    received_at=received_at,
                )
            )


def seed(db: Session) -> None:
    db.execute(delete(GoodsReceipt))
    db.execute(delete(PoLine))
    db.execute(delete(PurchaseOrder))
    db.execute(delete(Supplier))

    suppliers = _load_suppliers(db)
    po_lines_by_key = _load_purchase_orders(db, suppliers)
    _load_goods_receipts(db, po_lines_by_key)
    db.commit()


def main() -> None:
    with SessionLocal() as db:
        seed(db)


if __name__ == "__main__":
    main()
