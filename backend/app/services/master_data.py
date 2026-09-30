"""Postgres-backed lookups for the `match` and `risk` nodes (docs/spec.md
§2.1). Query here, decide in app.rules.* — the rule functions stay pure and
only see plain dicts/Pydantic models, per AGENTS.md rule 1.
"""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import GoodsReceipt, Invoice
from app.db.models import PoLine as PoLineModel
from app.db.models import PurchaseOrder as PurchaseOrderModel
from app.db.models import Supplier as SupplierModel
from app.schemas.invoice import BankAccount
from app.schemas.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.schemas.supplier import Supplier

# Invoices with this decision are excluded from accumulation/duplicate
# lookups: a rejected invoice was never a valid claim against the PO's
# allocation, and duplicates of it should still be flagged (see the
# partial unique index decision in PROGRESS.md 1.9).
_EXCLUDED_DECISION = "RECHAZAR"


def load_purchase_orders(db: Session) -> dict[str, PurchaseOrder]:
    orders = db.scalars(select(PurchaseOrderModel)).all()
    return {
        po.number: PurchaseOrder(
            number=po.number,
            supplier_nit=po.supplier.nit,
            lines=[
                PurchaseOrderLine(
                    sku=line.sku,
                    description=line.description,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    vat_rate=line.vat_rate,
                )
                for line in po.lines
            ],
        )
        for po in orders
    }


def load_received_quantity(db: Session) -> dict[tuple[str, str], Decimal]:
    rows = db.execute(
        select(PurchaseOrderModel.number, PoLineModel.sku, GoodsReceipt.quantity_received)
        .join(PoLineModel, PoLineModel.po_id == PurchaseOrderModel.id)
        .join(GoodsReceipt, GoodsReceipt.po_line_id == PoLineModel.id)
    ).all()

    received: dict[tuple[str, str], Decimal] = {}
    for number, sku, quantity_received in rows:
        key = (number, sku)
        received[key] = received.get(key, Decimal(0)) + quantity_received
    return received


def load_previously_invoiced_quantity(
    db: Session, exclude_invoice_id: uuid.UUID | None = None
) -> dict[tuple[str, str], Decimal]:
    """Sums invoiced quantity per (po_number, sku) across every past,
    non-rejected invoice — so `QTY_EXCEEDS_RECEIPT` catches a PO/SKU being
    over-invoiced across several separate invoices, not just within one."""
    query = select(Invoice.extracted).where(Invoice.decision != _EXCLUDED_DECISION)
    if exclude_invoice_id is not None:
        query = query.where(Invoice.id != exclude_invoice_id)

    accumulated: dict[tuple[str, str], Decimal] = {}
    extracted_rows: list[dict[str, Any] | None] = list(db.scalars(query))
    for extracted in extracted_rows:
        if extracted is None:
            continue
        po_number = extracted.get("purchase_order")
        if po_number is None:
            continue
        for line in extracted.get("lines", []):
            sku = line.get("sku")
            if sku is None:
                continue
            key = (po_number, sku)
            quantity = Decimal(str(line["quantity"]))
            accumulated[key] = accumulated.get(key, Decimal(0)) + quantity

    return accumulated


def load_suppliers(db: Session) -> dict[str, Supplier]:
    suppliers = db.scalars(select(SupplierModel)).all()
    return {
        supplier.nit: Supplier(
            nit=supplier.nit,
            dv=supplier.dv,
            name=supplier.name,
            email=supplier.email,
            status=supplier.status,  # type: ignore[arg-type]
            bank_account=BankAccount(
                bank=supplier.bank,
                account_type=supplier.account_type,  # type: ignore[arg-type]
                number=supplier.account_number,
            ),
        )
        for supplier in suppliers
    }


def load_previous_invoice_numbers(
    db: Session, exclude_invoice_id: uuid.UUID | None = None
) -> set[tuple[str, str]]:
    query = select(SupplierModel.nit, Invoice.invoice_number).join(
        SupplierModel, SupplierModel.id == Invoice.supplier_id
    )
    if exclude_invoice_id is not None:
        query = query.where(Invoice.id != exclude_invoice_id)
    return {(nit, invoice_number) for nit, invoice_number in db.execute(query)}


def load_previous_file_hashes(db: Session, exclude_invoice_id: uuid.UUID | None = None) -> set[str]:
    query = select(Invoice.file_hash)
    if exclude_invoice_id is not None:
        query = query.where(Invoice.id != exclude_invoice_id)
    return set(db.scalars(query))
