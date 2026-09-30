from decimal import Decimal

from pydantic import BaseModel


class PurchaseOrderLine(BaseModel):
    sku: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    vat_rate: Decimal


class PurchaseOrder(BaseModel):
    number: str
    supplier_nit: str
    lines: list[PurchaseOrderLine]
