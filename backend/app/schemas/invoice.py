from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class InvoiceLine(BaseModel):
    sku: str | None
    description: str
    quantity: Decimal
    unit_price: Decimal
    vat_rate: Decimal
    line_subtotal: Decimal


class BankAccount(BaseModel):
    bank: str
    account_type: Literal["Ahorros", "Corriente"]
    number: str


class ExtractedInvoice(BaseModel):
    supplier_nit: str
    supplier_dv: int | None
    supplier_name: str
    invoice_number: str
    issue_date: date
    due_date: date | None
    purchase_order: str | None
    currency: Literal["COP"] = "COP"
    lines: list[InvoiceLine]
    subtotal: Decimal
    vat_total: Decimal
    total: Decimal
    cufe: str | None
    bank_account: BankAccount | None
