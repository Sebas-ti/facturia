from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Invoice, PoLine, PurchaseOrder, Supplier
from app.db.session import get_db
from app.schemas.master_data import PoLineDetail, PurchaseOrderItem, SupplierItem

router = APIRouter(tags=["master-data"])


@router.get("/api/suppliers", response_model=list[SupplierItem])
def list_suppliers(
    search: str | None = Query(default=None, description="Búsqueda por nombre o NIT"),
    status: str | None = Query(default=None, description="Filtrar por estado (ACTIVO, INACTIVO)"),
    db: Session = Depends(get_db),  # noqa: B008
) -> list[SupplierItem]:
    query = select(Supplier).order_by(Supplier.name.asc())

    if status:
        query = query.where(Supplier.status == status)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(Supplier.name.ilike(pattern), Supplier.nit.ilike(pattern)))

    suppliers = db.scalars(query).all()

    # Calculate counts per supplier
    po_counts = dict(
        db.execute(
            select(PurchaseOrder.supplier_id, func.count(PurchaseOrder.id)).group_by(
                PurchaseOrder.supplier_id
            )
        ).all()
    )
    inv_counts = dict(
        db.execute(
            select(Invoice.supplier_id, func.count(Invoice.id))
            .where(Invoice.supplier_id.is_not(None))
            .group_by(Invoice.supplier_id)
        ).all()
    )

    items: list[SupplierItem] = []
    for s in suppliers:
        items.append(
            SupplierItem(
                id=s.id,
                nit=s.nit,
                dv=s.dv,
                name=s.name,
                email=s.email,
                bank=s.bank,
                account_type=s.account_type,
                account_number=s.account_number,
                status=s.status,
                purchase_orders_count=po_counts.get(s.id, 0),
                invoices_count=inv_counts.get(s.id, 0),
            )
        )
    return items


@router.get("/api/suppliers/{supplier_id}", response_model=SupplierItem)
def get_supplier(
    supplier_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
) -> SupplierItem:
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")

    po_count = (
        db.scalar(
            select(func.count(PurchaseOrder.id)).where(PurchaseOrder.supplier_id == supplier.id)
        )
        or 0
    )
    inv_count = (
        db.scalar(select(func.count(Invoice.id)).where(Invoice.supplier_id == supplier.id)) or 0
    )

    return SupplierItem(
        id=supplier.id,
        nit=supplier.nit,
        dv=supplier.dv,
        name=supplier.name,
        email=supplier.email,
        bank=supplier.bank,
        account_type=supplier.account_type,
        account_number=supplier.account_number,
        status=supplier.status,
        purchase_orders_count=po_count,
        invoices_count=inv_count,
    )


@router.get("/api/purchase-orders", response_model=list[PurchaseOrderItem])
def list_purchase_orders(
    number: str | None = Query(default=None, description="Filtrar por número de orden de compra"),
    supplier_nit: str | None = Query(default=None, description="Filtrar por NIT del proveedor"),
    status: str | None = Query(default=None, description="Filtrar por estado"),
    db: Session = Depends(get_db),  # noqa: B008
) -> list[PurchaseOrderItem]:
    query = (
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.supplier),
            selectinload(PurchaseOrder.lines).selectinload(PoLine.goods_receipts),
        )
        .order_by(PurchaseOrder.date.desc())
    )

    if number:
        query = query.where(PurchaseOrder.number.ilike(f"%{number.strip()}%"))
    if supplier_nit:
        query = query.where(PurchaseOrder.supplier.has(Supplier.nit == supplier_nit.strip()))
    if status:
        query = query.where(PurchaseOrder.status == status)

    orders = db.scalars(query).all()

    items: list[PurchaseOrderItem] = []
    for po in orders:
        lines: list[PoLineDetail] = []
        total_order = Decimal(0)

        for line in po.lines:
            line_subtotal = round(line.quantity * line.unit_price, 2)
            total_order += line_subtotal
            qty_received = sum((r.quantity_received for r in line.goods_receipts), Decimal(0))
            lines.append(
                PoLineDetail(
                    id=line.id,
                    sku=line.sku,
                    description=line.description,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    vat_rate=line.vat_rate,
                    line_subtotal=line_subtotal,
                    quantity_received=qty_received,
                )
            )

        items.append(
            PurchaseOrderItem(
                id=po.id,
                number=po.number,
                supplier_id=po.supplier_id,
                supplier_name=po.supplier.name if po.supplier else "Desconocido",
                supplier_nit=po.supplier.nit if po.supplier else "",
                date=po.date,
                status=po.status,
                total=total_order,
                lines_count=len(lines),
                lines=lines,
            )
        )

    return items


@router.get("/api/purchase-orders/{number_or_id}", response_model=PurchaseOrderItem)
def get_purchase_order(
    number_or_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> PurchaseOrderItem:
    query = (
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.supplier),
            selectinload(PurchaseOrder.lines).selectinload(PoLine.goods_receipts),
        )
    )

    try:
        uuid_val = UUID(number_or_id)
        query = query.where(or_(PurchaseOrder.id == uuid_val, PurchaseOrder.number == number_or_id))
    except ValueError:
        query = query.where(PurchaseOrder.number == number_or_id)

    po = db.scalars(query).first()
    if not po:
        raise HTTPException(
            status_code=404, detail=f"Orden de compra '{number_or_id}' no encontrada."
        )

    lines: list[PoLineDetail] = []
    total_order = Decimal(0)
    for line in po.lines:
        line_subtotal = round(line.quantity * line.unit_price, 2)
        total_order += line_subtotal
        qty_received = sum((r.quantity_received for r in line.goods_receipts), Decimal(0))
        lines.append(
            PoLineDetail(
                id=line.id,
                sku=line.sku,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                vat_rate=line.vat_rate,
                line_subtotal=line_subtotal,
                quantity_received=qty_received,
            )
        )

    return PurchaseOrderItem(
        id=po.id,
        number=po.number,
        supplier_id=po.supplier_id,
        supplier_name=po.supplier.name if po.supplier else "Desconocido",
        supplier_nit=po.supplier.nit if po.supplier else "",
        date=po.date,
        status=po.status,
        total=total_order,
        lines_count=len(lines),
        lines=lines,
    )
