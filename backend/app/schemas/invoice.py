from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.finding import Finding, FindingCode, Severity


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


class InvoiceFindingSummary(BaseModel):
    id: UUID
    code: FindingCode | str
    severity: Severity
    message: str


class InvoiceListItem(BaseModel):
    id: UUID
    file_hash: str
    status: str
    decision: str | None = None
    supplier_id: UUID | None = None
    supplier_name: str | None = None
    supplier_nit: str | None = None
    invoice_number: str
    issue_date: date | None = None
    total: Decimal
    created_at: datetime
    processed_ms: int | None = None
    cost_usd: Decimal | None = None
    findings: list[InvoiceFindingSummary] = []
    has_bank_account_alert: bool = False


class InvoiceListResponse(BaseModel):
    items: list[InvoiceListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class ThreeWayMatchLine(BaseModel):
    sku: str | None = None
    description: str
    invoice_qty: Decimal
    invoice_unit_price: Decimal
    po_qty: Decimal | None = None
    po_unit_price: Decimal | None = None
    received_qty: Decimal | None = None
    price_variance_pct: float | None = None
    status: Literal["MATCH", "PRICE_MISMATCH", "QTY_MISMATCH", "MISSING_PO_LINE", "NO_PO"] = "MATCH"


class PurchaseOrderDetailSummary(BaseModel):
    number: str
    date: date
    status: str
    lines_count: int


class InvoiceDetailResponse(BaseModel):
    id: UUID
    file_hash: str
    blob_url: str
    status: str
    decision: str | None = None
    supplier_id: UUID | None = None
    supplier_name: str | None = None
    supplier_nit: str | None = None
    invoice_number: str
    issue_date: date | None = None
    due_date: date | None = None
    purchase_order_number: str | None = None
    currency: str = "COP"
    subtotal: Decimal
    vat_total: Decimal
    total: Decimal
    cufe: str | None = None
    bank_account: BankAccount | None = None
    lines: list[InvoiceLine] = []
    field_confidence: dict[str, float] = {}
    findings: list[Finding] = []
    explanation: str | None = None
    supplier_email_draft: str | None = None
    three_way_match: list[ThreeWayMatchLine] = []
    purchase_order: PurchaseOrderDetailSummary | None = None
    created_at: datetime
    processed_ms: int | None = None
    cost_usd: Decimal | None = None
    has_bank_account_alert: bool = False


class InvoiceFileResponse(BaseModel):
    url: str
    file_hash: str
    expires_in_seconds: int = 3600


class AgentRunItem(BaseModel):
    id: UUID
    invoice_id: UUID
    node: str
    started_at: datetime
    duration_ms: int
    tokens_in: int | None = None
    tokens_out: int | None = None
    output: dict[str, Any] | None = None


class InvoiceTraceResponse(BaseModel):
    invoice_id: UUID
    status: str
    decision: str | None = None
    total_duration_ms: int
    total_tokens_in: int
    total_tokens_out: int
    cost_usd: Decimal | None = None
    runs: list[AgentRunItem]

