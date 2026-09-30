"""POST /api/invoices, GET /api/invoices, and GET /api/invoices/{id}/events (docs/spec.md §6).

Upload always calls real Azure (Document Intelligence, OpenAI) — the user
chose "siempre real" over a mock toggle for this endpoint, matching how the
deployed product actually behaves (PROGRESS.md 4.2).
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, UploadFile
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from pydantic import ValidationError
from sqlalchemy import case, exists, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.models import AgentRun, FindingRecord, Invoice, PoLine, PurchaseOrder, Review, Supplier
from app.db.session import SessionLocal, get_db
from app.graph import GRAPH_NODE_ORDER, GraphState, build_graph
from app.schemas.finding import Finding, FindingCode
from app.schemas.invoice import (
    AgentRunItem,
    BankAccount,
    InvoiceDetailResponse,
    InvoiceFileResponse,
    InvoiceFindingSummary,
    InvoiceLine,
    InvoiceListItem,
    InvoiceListResponse,
    InvoiceTraceResponse,
    PurchaseOrderDetailSummary,
    ThreeWayMatchLine,
)
from app.schemas.review import ReviewCreate, ReviewResponse
from app.services.auth import require_api_key
from app.services.blob import BlobStorageClient
from app.services.checkpoint import build_checkpointer
from app.services.doc_intelligence import AzureDocumentIntelligenceClient
from app.services.explain import AzureDecisionExplainerClient
from app.services.llm import AzureInvoiceLLMClient

router = APIRouter(prefix="/api/invoices", tags=["invoices"])
logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
SSE_POLL_INTERVAL_SECONDS = 0.4
SSE_TIMEOUT_SECONDS = 120.0


@router.get("", response_model=InvoiceListResponse)
def list_invoices(
    status: str | None = Query(default=None, description="Filtrar por estado (PROCESSING, PROCESSED, ERROR)"),
    decision: str | None = Query(default=None, description="Filtrar por decisión (APROBAR, REVISION, RECHAZAR)"),
    supplier: str | None = Query(default=None, description="Filtrar por nombre o NIT del proveedor"),
    search: str | None = Query(default=None, description="Búsqueda libre por número de factura o proveedor"),
    bank_account_alert: bool | None = Query(
        default=None, description="Filtrar solo facturas con cambio de cuenta bancaria"
    ),
    page: int = Query(default=1, ge=1, description="Número de página (base 1)"),
    page_size: int = Query(default=10, ge=1, le=100, description="Cantidad de facturas por página"),
    db: Session = Depends(get_db),  # noqa: B008
) -> InvoiceListResponse:
    conditions = []
    if status:
        conditions.append(Invoice.status == status)
    if decision:
        conditions.append(Invoice.decision == decision)
    if supplier:
        supp_pat = f"%{supplier.strip()}%"
        conditions.append(
            or_(
                Invoice.supplier.has(Supplier.name.ilike(supp_pat)),
                Invoice.supplier.has(Supplier.nit.ilike(supp_pat)),
                Invoice.extracted["supplier_name"].astext.ilike(supp_pat),
                Invoice.extracted["supplier_nit"].astext.ilike(supp_pat),
            )
        )
    if search:
        search_pat = f"%{search.strip()}%"
        conditions.append(
            or_(
                Invoice.invoice_number.ilike(search_pat),
                Invoice.supplier.has(Supplier.name.ilike(search_pat)),
                Invoice.supplier.has(Supplier.nit.ilike(search_pat)),
                Invoice.extracted["supplier_name"].astext.ilike(search_pat),
                Invoice.extracted["supplier_nit"].astext.ilike(search_pat),
            )
        )

    has_bank_alert_expr = exists(
        select(1).where(
            FindingRecord.invoice_id == Invoice.id,
            FindingRecord.code == FindingCode.BANK_ACCOUNT_CHANGED.value,
        )
    )

    if bank_account_alert is True:
        conditions.append(has_bank_alert_expr)
    elif bank_account_alert is False:
        conditions.append(~has_bank_alert_expr)

    count_query = select(func.count(Invoice.id))
    for cond in conditions:
        count_query = count_query.where(cond)
    total = db.scalar(count_query) or 0

    items_query = (
        select(Invoice)
        .options(
            joinedload(Invoice.supplier),
            selectinload(Invoice.findings),
        )
    )
    for cond in conditions:
        items_query = items_query.where(cond)

    items_query = (
        items_query
        .order_by(
            case((has_bank_alert_expr, 0), else_=1),
            Invoice.created_at.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    invoices = db.scalars(items_query).unique().all()

    items: list[InvoiceListItem] = []
    for inv in invoices:
        supplier_name = (
            inv.supplier.name
            if inv.supplier
            else (inv.extracted.get("supplier_name") if inv.extracted else None)
        )
        supplier_nit = (
            inv.supplier.nit
            if inv.supplier
            else (inv.extracted.get("supplier_nit") if inv.extracted else None)
        )

        issue_date: date | None = None
        if inv.extracted and inv.extracted.get("issue_date"):
            try:
                issue_date = date.fromisoformat(str(inv.extracted["issue_date"]))
            except (ValueError, TypeError):
                issue_date = None

        has_bank_alert = any(
            f.code == FindingCode.BANK_ACCOUNT_CHANGED.value for f in inv.findings
        )
        findings_summary = [
            InvoiceFindingSummary(
                id=f.id,
                code=f.code,
                severity=f.severity,  # type: ignore[arg-type]
                message=f.message,
            )
            for f in inv.findings
        ]

        items.append(
            InvoiceListItem(
                id=inv.id,
                file_hash=inv.file_hash,
                status=inv.status,
                decision=inv.decision,
                supplier_id=inv.supplier_id,
                supplier_name=supplier_name,
                supplier_nit=supplier_nit,
                invoice_number=inv.invoice_number,
                issue_date=issue_date,
                total=inv.total,
                created_at=inv.created_at,
                processed_ms=inv.processed_ms,
                cost_usd=inv.cost_usd,
                findings=findings_summary,
                has_bank_account_alert=has_bank_alert,
            )
        )

    total_pages = max(1, (total + page_size - 1) // page_size)

    return InvoiceListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", status_code=202, dependencies=[Depends(require_api_key)])
async def create_invoice(file: UploadFile, background_tasks: BackgroundTasks) -> dict[str, str]:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=422, detail="El archivo debe ser un PDF.")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=422, detail="El archivo supera los 5 MB permitidos.")

    invoice_id = uuid4()
    with SessionLocal() as db:
        db.add(
            Invoice(
                id=invoice_id,
                file_hash="pending",
                blob_url="pending",
                status="PROCESSING",
                invoice_number="PENDIENTE",
                total=Decimal(0),
            )
        )
        db.commit()

    background_tasks.add_task(_process_invoice, invoice_id, pdf_bytes)

    return {"invoice_id": str(invoice_id)}


def _process_invoice(invoice_id: UUID, pdf_bytes: bytes) -> None:
    with SessionLocal() as db, build_checkpointer() as checkpointer:
        graph = build_graph(
            db=db,
            doc_intelligence=AzureDocumentIntelligenceClient(),
            llm=AzureInvoiceLLMClient(),
            blob=BlobStorageClient(),
            explainer=AzureDecisionExplainerClient(),
            checkpointer=checkpointer,
            trace=True,
        )
        initial_state: GraphState = {
            "invoice_id": invoice_id,
            "file_hash": "",
            "is_scanned": False,
            "extracted": None,
            "field_confidence": {},
            "findings": [],
            "decision": None,
            "explanation": None,
            "supplier_email_draft": None,
            "pdf_bytes": pdf_bytes,
            "blob_url": "",
        }
        config: RunnableConfig = {"configurable": {"thread_id": str(invoice_id)}}

        try:
            result: dict[str, Any] = graph.invoke(initial_state, config=config)
        except Exception:
            logger.exception("Pipeline failed for invoice %s", invoice_id)
            invoice = db.get(Invoice, invoice_id)
            if invoice is not None:
                invoice.status = "ERROR"
                db.commit()
            raise

        _save_result(db, invoice_id, result)


def _save_result(db: Session, invoice_id: UUID, result: dict[str, Any]) -> None:
    extracted = result["extracted"]
    supplier_id = None
    if extracted is not None:
        supplier_id = db.scalars(
            select(Supplier.id).where(Supplier.nit == extracted.supplier_nit)
        ).first()

    invoice = db.get(Invoice, invoice_id)
    assert invoice is not None

    invoice.file_hash = result["file_hash"]
    invoice.blob_url = result["blob_url"]
    invoice.status = "PROCESSED"
    invoice.decision = result["decision"]
    invoice.supplier_id = supplier_id
    invoice.invoice_number = extracted.invoice_number if extracted else "DESCONOCIDO"
    invoice.total = extracted.total if extracted else Decimal(0)
    invoice.extracted = extracted.model_dump(mode="json") if extracted else None

    runs = db.scalars(
        select(AgentRun).where(AgentRun.invoice_id == invoice_id)
    ).all()
    total_duration_ms = sum((r.duration_ms or 0) for r in runs)
    total_tokens_in = sum((r.tokens_in or 0) for r in runs)
    total_tokens_out = sum((r.tokens_out or 0) for r in runs)
    doc_intel_cost = Decimal("0.0100")
    llm_cost = (Decimal(total_tokens_in) * Decimal("0.00000015")) + (
        Decimal(total_tokens_out) * Decimal("0.00000060")
    )
    invoice.processed_ms = total_duration_ms
    invoice.cost_usd = round(doc_intel_cost + llm_cost, 4)

    for finding in result["findings"]:
        db.add(
            FindingRecord(
                invoice_id=invoice_id,
                code=finding.code.value,
                severity=finding.severity,
                message=finding.message,
                evidence=finding.evidence,
            )
        )

    db.commit()


@router.get("/{invoice_id}/events")
async def stream_invoice_events(invoice_id: UUID) -> StreamingResponse:
    return StreamingResponse(_invoice_event_stream(invoice_id), media_type="text/event-stream")


async def _invoice_event_stream(invoice_id: UUID) -> AsyncIterator[str]:
    seen_nodes: set[str] = set()
    elapsed = 0.0

    while elapsed < SSE_TIMEOUT_SECONDS:
        with SessionLocal() as db:
            invoice = db.get(Invoice, invoice_id)
            if invoice is None:
                yield _sse_event("error", {"detail": "Factura no encontrada"})
                return

            run_nodes = db.scalars(
                select(AgentRun.node)
                .where(AgentRun.invoice_id == invoice_id)
                .order_by(AgentRun.started_at)
            ).all()
            for node in run_nodes:
                if node not in seen_nodes:
                    seen_nodes.add(node)
                    yield _sse_event("progress", {"node": node, "total_nodes": len(GRAPH_NODE_ORDER)})

            if invoice.status in ("PROCESSED", "ERROR"):
                yield _sse_event(
                    "done", {"status": invoice.status, "decision": invoice.decision}
                )
                return

        await asyncio.sleep(SSE_POLL_INTERVAL_SECONDS)
        elapsed += SSE_POLL_INTERVAL_SECONDS

    yield _sse_event("error", {"detail": "Tiempo de espera agotado"})


def _sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/{invoice_id}", response_model=InvoiceDetailResponse)
def get_invoice(
    invoice_id: UUID, db: Session = Depends(get_db)  # noqa: B008
) -> InvoiceDetailResponse:
    invoice = (
        db.scalars(
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .options(
                joinedload(Invoice.supplier),
                selectinload(Invoice.findings),
                selectinload(Invoice.agent_runs),
            )
        )
        .unique()
        .first()
    )
    if invoice is None:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    extracted = invoice.extracted or {}
    supplier_name = (
        invoice.supplier.name
        if invoice.supplier
        else extracted.get("supplier_name")
    )
    supplier_nit = (
        invoice.supplier.nit
        if invoice.supplier
        else extracted.get("supplier_nit")
    )

    issue_date: date | None = None
    if extracted.get("issue_date"):
        try:
            issue_date = date.fromisoformat(str(extracted["issue_date"]))
        except (ValueError, TypeError):
            issue_date = None

    due_date: date | None = None
    if extracted.get("due_date"):
        try:
            due_date = date.fromisoformat(str(extracted["due_date"]))
        except (ValueError, TypeError):
            due_date = None

    field_confidence: dict[str, float] = {}
    explanation: str | None = None
    supplier_email_draft: str | None = None

    for run in invoice.agent_runs:
        if run.node == "extract" and run.output:
            field_confidence = run.output.get("field_confidence", {})
        elif run.node == "decide" and run.output:
            explanation = run.output.get("explanation")
            supplier_email_draft = run.output.get("supplier_email_draft")

    po_number = extracted.get("purchase_order")
    po_summary: PurchaseOrderDetailSummary | None = None
    three_way_match: list[ThreeWayMatchLine] = []

    po = None
    if po_number:
        po = (
            db.scalars(
                select(PurchaseOrder)
                .where(PurchaseOrder.number == str(po_number).strip())
                .options(
                    joinedload(PurchaseOrder.lines).joinedload(PoLine.goods_receipts)
                )
            )
            .unique()
            .first()
        )

    po_lines_by_sku: dict[str, tuple[PoLine, Decimal]] = {}
    if po:
        po_summary = PurchaseOrderDetailSummary(
            number=po.number,
            date=po.date,
            status=po.status,
            lines_count=len(po.lines),
        )
        for line in po.lines:
            rec_qty = sum(
                (gr.quantity_received for gr in line.goods_receipts), Decimal(0)
            )
            po_lines_by_sku[line.sku] = (line, rec_qty)

    invoice_lines: list[InvoiceLine] = []
    for l_dict in extracted.get("lines", []):
        try:
            inv_line = InvoiceLine(**l_dict)
            invoice_lines.append(inv_line)

            sku = inv_line.sku
            inv_qty = inv_line.quantity
            inv_price = inv_line.unit_price

            if sku and sku in po_lines_by_sku:
                po_line, rec_qty = po_lines_by_sku[sku]
                variance = (
                    round(float(abs(inv_price - po_line.unit_price) / po_line.unit_price * 100), 2)
                    if po_line.unit_price > 0
                    else 0.0
                )
                match_status: Literal["MATCH", "PRICE_MISMATCH", "QTY_MISMATCH"]
                if variance > 2.0:
                    match_status = "PRICE_MISMATCH"
                elif inv_qty > rec_qty:
                    match_status = "QTY_MISMATCH"
                else:
                    match_status = "MATCH"

                three_way_match.append(
                    ThreeWayMatchLine(
                        sku=sku,
                        description=inv_line.description,
                        invoice_qty=inv_qty,
                        invoice_unit_price=inv_price,
                        po_qty=po_line.quantity,
                        po_unit_price=po_line.unit_price,
                        received_qty=rec_qty,
                        price_variance_pct=variance,
                        status=match_status,
                    )
                )
            elif po:
                three_way_match.append(
                    ThreeWayMatchLine(
                        sku=sku,
                        description=inv_line.description,
                        invoice_qty=inv_qty,
                        invoice_unit_price=inv_price,
                        status="MISSING_PO_LINE",
                    )
                )
            else:
                three_way_match.append(
                    ThreeWayMatchLine(
                        sku=sku,
                        description=inv_line.description,
                        invoice_qty=inv_qty,
                        invoice_unit_price=inv_price,
                        status="NO_PO",
                    )
                )
        except (ValidationError, TypeError, KeyError, ValueError) as e:
            logger.warning("Error parsing invoice line: %s", e)

    bank_account: BankAccount | None = None
    if extracted.get("bank_account"):
        try:
            bank_account = BankAccount(**extracted["bank_account"])
        except (ValidationError, TypeError, KeyError):
            bank_account = None

    findings = [
        Finding(
            code=f.code,  # type: ignore[arg-type]
            severity=f.severity,  # type: ignore[arg-type]
            message=f.message,
            evidence=f.evidence or {},
        )
        for f in invoice.findings
    ]

    has_bank_alert = any(
        f.code == FindingCode.BANK_ACCOUNT_CHANGED.value for f in invoice.findings
    )
    processed_ms = (
        sum(r.duration_ms for r in invoice.agent_runs)
        if invoice.agent_runs
        else invoice.processed_ms
    )

    return InvoiceDetailResponse(
        id=invoice.id,
        file_hash=invoice.file_hash,
        blob_url=invoice.blob_url,
        status=invoice.status,
        decision=invoice.decision,
        supplier_id=invoice.supplier_id,
        supplier_name=supplier_name,
        supplier_nit=supplier_nit,
        invoice_number=invoice.invoice_number,
        issue_date=issue_date,
        due_date=due_date,
        purchase_order_number=po_number,
        currency=extracted.get("currency", "COP"),
        subtotal=Decimal(str(extracted.get("subtotal", invoice.total))),
        vat_total=Decimal(str(extracted.get("vat_total", 0))),
        total=invoice.total,
        cufe=extracted.get("cufe"),
        bank_account=bank_account,
        lines=invoice_lines,
        field_confidence=field_confidence,
        findings=findings,
        explanation=explanation,
        supplier_email_draft=supplier_email_draft,
        three_way_match=three_way_match,
        purchase_order=po_summary,
        created_at=invoice.created_at,
        processed_ms=processed_ms,
        cost_usd=invoice.cost_usd,
        has_bank_account_alert=has_bank_alert,
    )


@router.get("/{invoice_id}/file", response_model=InvoiceFileResponse)
def get_invoice_file(
    invoice_id: UUID,
    stream: bool = Query(default=False, description="Descargar el contenido del PDF directamente"),
    db: Session = Depends(get_db),  # noqa: B008
) -> Any:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    blob_client = BlobStorageClient()
    if stream:
        try:
            pdf_bytes = blob_client.download_pdf(invoice.file_hash)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'inline; filename="{invoice.invoice_number or invoice.id}.pdf"'
                },
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not download blob directly for invoice %s: %s", invoice_id, e)
            raise HTTPException(status_code=404, detail="Archivo PDF no encontrado en almacenamiento")

    sas_url = blob_client.generate_sas_url(invoice.file_hash)
    return InvoiceFileResponse(
        url=sas_url,
        file_hash=invoice.file_hash,
        expires_in_seconds=3600,
    )


@router.get("/{invoice_id}/trace", response_model=InvoiceTraceResponse)
def get_invoice_trace(
    invoice_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
) -> InvoiceTraceResponse:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    runs = db.scalars(
        select(AgentRun)
        .where(AgentRun.invoice_id == invoice_id)
        .order_by(AgentRun.started_at.asc())
    ).all()

    run_items = [
        AgentRunItem(
            id=r.id,
            invoice_id=r.invoice_id,
            node=r.node,
            started_at=r.started_at,
            duration_ms=r.duration_ms,
            tokens_in=r.tokens_in,
            tokens_out=r.tokens_out,
            output=r.output,
        )
        for r in runs
    ]

    total_duration_ms = (
        sum(r.duration_ms for r in run_items) if run_items else (invoice.processed_ms or 0)
    )
    total_tokens_in = sum(r.tokens_in or 0 for r in run_items)
    total_tokens_out = sum(r.tokens_out or 0 for r in run_items)

    return InvoiceTraceResponse(
        invoice_id=invoice.id,
        status=invoice.status,
        decision=invoice.decision,
        total_duration_ms=total_duration_ms,
        total_tokens_in=total_tokens_in,
        total_tokens_out=total_tokens_out,
        cost_usd=invoice.cost_usd,
        runs=run_items,
    )


def _resume_graph(invoice_id: UUID, action: str) -> None:
    try:
        with SessionLocal() as db, build_checkpointer() as checkpointer:
            graph = build_graph(
                db=db,
                doc_intelligence=AzureDocumentIntelligenceClient(),
                llm=AzureInvoiceLLMClient(),
                blob=BlobStorageClient(),
                explainer=AzureDecisionExplainerClient(),
                checkpointer=checkpointer,
                trace=True,
            )
            config: RunnableConfig = {"configurable": {"thread_id": str(invoice_id)}}
            graph.invoke(Command(resume=action), config=config)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "Could not resume LangGraph checkpoint for invoice %s (proceeding with DB update): %s",
            invoice_id,
            e,
        )


@router.post("/{invoice_id}/review", response_model=ReviewResponse)
def review_invoice(
    invoice_id: UUID,
    payload: ReviewCreate,
    db: Session = Depends(get_db),  # noqa: B008
) -> ReviewResponse:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    if invoice.decision != "REVISION":
        raise HTTPException(
            status_code=400,
            detail=f"La factura está en estado '{invoice.decision}'. Solo facturas en REVISION pueden ser revisadas.",
        )

    previous_decision = invoice.decision

    # 1. Resume LangGraph graph checkpoint
    _resume_graph(invoice_id, payload.action)

    # 2. Record human review in database
    review = Review(
        id=uuid4(),
        invoice_id=invoice_id,
        reviewer=payload.reviewer,
        action=payload.action,
        comment=payload.comment,
        created_at=datetime.now(UTC),
    )
    db.add(review)

    # 3. Update invoice decision
    invoice.decision = payload.action
    db.commit()
    db.refresh(review)

    return ReviewResponse(
        id=review.id,
        invoice_id=review.invoice_id,
        reviewer=review.reviewer,
        action=review.action,
        comment=review.comment,
        created_at=review.created_at,
        previous_decision=previous_decision,
        new_decision=invoice.decision,
    )


