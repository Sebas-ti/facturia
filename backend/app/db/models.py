import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nit: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    dv: Mapped[int]
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    bank: Mapped[str] = mapped_column(String(100))
    account_type: Mapped[str] = mapped_column(String(20))
    account_number: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))

    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(back_populates="supplier")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="supplier")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("suppliers.id"))
    date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20))

    supplier: Mapped["Supplier"] = relationship(back_populates="purchase_orders")
    lines: Mapped[list["PoLine"]] = relationship(back_populates="purchase_order")


class PoLine(Base):
    __tablename__ = "po_lines"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    po_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("purchase_orders.id"))
    sku: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2))

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="lines")
    goods_receipts: Mapped[list["GoodsReceipt"]] = relationship(back_populates="po_line")


class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    po_line_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("po_lines.id"))
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    po_line: Mapped["PoLine"] = relationship(back_populates="goods_receipts")


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_file_hash", "file_hash"),
        # Excludes RECHAZAR from the uniqueness check: a duplicate invoice is
        # deliberately rejected and re-inserted with the same (supplier_id,
        # invoice_number) as the original, see docs/spec.md §5. Non-duplicate
        # rejections (e.g. ARITHMETIC_ERROR) are excluded too, since the
        # invoice row alone doesn't carry which finding caused the rejection.
        Index(
            "uq_invoices_supplier_number_active",
            "supplier_id",
            "invoice_number",
            unique=True,
            postgresql_where=text("decision IS DISTINCT FROM 'RECHAZAR'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    file_hash: Mapped[str] = mapped_column(String(64))
    blob_url: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))
    decision: Mapped[str | None] = mapped_column(String(20))
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("suppliers.id"))
    invoice_number: Mapped[str] = mapped_column(String(50))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    extracted: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_ms: Mapped[int | None]
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))

    supplier: Mapped[Supplier | None] = relationship(back_populates="invoices")
    findings: Mapped[list["FindingRecord"]] = relationship(back_populates="invoice")
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="invoice")
    reviews: Mapped[list["Review"]] = relationship(back_populates="invoice")


class FindingRecord(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"))
    code: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB)

    invoice: Mapped["Invoice"] = relationship(back_populates="findings")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"))
    node: Mapped[str] = mapped_column(String(50))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int]
    tokens_in: Mapped[int | None]
    tokens_out: Mapped[int | None]
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    invoice: Mapped["Invoice"] = relationship(back_populates="agent_runs")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"))
    reviewer: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(20))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    invoice: Mapped["Invoice"] = relationship(back_populates="reviews")
