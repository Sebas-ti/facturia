from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class SupplierItem(BaseModel):
    id: UUID
    nit: str
    dv: int
    name: str
    email: str
    bank: str
    account_type: str
    account_number: str
    status: str
    purchase_orders_count: int = 0
    invoices_count: int = 0


class PoLineDetail(BaseModel):
    id: UUID
    sku: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    vat_rate: Decimal
    line_subtotal: Decimal
    quantity_received: Decimal


class PurchaseOrderItem(BaseModel):
    id: UUID
    number: str
    supplier_id: UUID
    supplier_name: str
    supplier_nit: str
    date: date
    status: str
    total: Decimal
    lines_count: int
    lines: list[PoLineDetail] = []
