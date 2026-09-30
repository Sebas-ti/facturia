import csv
import json
from decimal import Decimal
from pathlib import Path

from app.schemas.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.schemas.supplier import Supplier

DATA_DIR = Path(__file__).parents[2] / "data"


def load_suppliers() -> dict[str, Supplier]:
    with (DATA_DIR / "proveedores.csv").open(encoding="utf-8") as f:
        return {
            row["nit"]: Supplier(
                nit=row["nit"],
                dv=int(row["dv"]),
                name=row["razon_social"],
                email=row["email"],
                status=row["estado"],
                bank_account={
                    "bank": row["banco"],
                    "account_type": row["tipo_cuenta"],
                    "number": row["cuenta"],
                },
            )
            for row in csv.DictReader(f)
        }


def load_purchase_orders() -> dict[str, PurchaseOrder]:
    raw = json.loads((DATA_DIR / "ordenes_compra.json").read_text(encoding="utf-8"))
    return {
        oc["numero"]: PurchaseOrder(
            number=oc["numero"],
            supplier_nit=oc["proveedor_nit"],
            lines=[
                PurchaseOrderLine(
                    sku=linea["sku"],
                    description=linea["descripcion"],
                    quantity=linea["cantidad"],
                    unit_price=linea["precio_unitario"],
                    vat_rate=linea["iva_pct"],
                )
                for linea in oc["lineas"]
            ],
        )
        for oc in raw
    }


def load_received_quantities() -> dict[tuple[str, str], Decimal]:
    received: dict[tuple[str, str], Decimal] = {}
    with (DATA_DIR / "recepciones.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["orden_compra"], row["sku"])
            received[key] = received.get(key, Decimal(0)) + Decimal(row["cantidad_recibida"])
    return received
