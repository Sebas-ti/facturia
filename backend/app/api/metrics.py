from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import Date, case, desc, exists, func, or_, select
from sqlalchemy.orm import Session

from app.db.models import AgentRun, FindingRecord, Invoice, Review
from app.db.session import get_db
from app.schemas.metrics import (
    DailyDecisionPoint,
    DecisionBreakdown,
    FindingMetricItem,
    MetricsKPIs,
    MetricsResponse,
)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

FINDING_LABELS: dict[str, str] = {
    "INVALID_NIT_DV": "Dígito de verificación NIT erróneo",
    "ARITHMETIC_ERROR": "Error aritmético en totales o líneas",
    "INVALID_CUFE": "Formato de CUFE inválido",
    "INCOHERENT_DATES": "Fechas incoherentes (emisión / vencimiento)",
    "UNKNOWN_SUPPLIER": "Proveedor no registrado en maestro",
    "MISSING_PO": "Sin orden de compra de referencia",
    "PRICE_MISMATCH": "Discrepancia de precio vs orden de compra (>2%)",
    "QTY_EXCEEDS_RECEIPT": "Cantidad facturada excede recepción",
    "DUPLICATE_INVOICE": "Factura duplicada",
    "BANK_ACCOUNT_CHANGED": "Cambio no autorizado de cuenta bancaria",
    "LOW_CONFIDENCE_EXTRACTION": "Baja confianza en extracción OCR",
    "AMOUNT_OVER_THRESHOLD": "Monto excede umbral de aprobación automática",
}


@router.get("", response_model=MetricsResponse)
def get_metrics(db: Session = Depends(get_db)) -> MetricsResponse:  # noqa: B008
    total_invoices = db.scalar(select(func.count(Invoice.id))) or 0
    processed_invoices = (
        db.scalar(select(func.count(Invoice.id)).where(Invoice.status == "PROCESSED"))
        or 0
    )

    # Auto-approved: approved by agent pipeline with no human review record
    auto_approved_count = (
        db.scalar(
            select(func.count(Invoice.id)).where(
                Invoice.decision == "APROBAR",
                ~exists(select(1).where(Review.invoice_id == Invoice.id)),
            )
        )
        or 0
    )

    auto_approval_rate_pct = (
        round((auto_approved_count / processed_invoices) * 100.0, 1)
        if processed_invoices > 0
        else 0.0
    )

    # Average processing time
    avg_time_val = db.scalar(
        select(func.avg(Invoice.processed_ms)).where(Invoice.processed_ms.is_not(None))
    )
    if avg_time_val is None:
        subq = (
            select(func.sum(AgentRun.duration_ms).label("total_ms"))
            .group_by(AgentRun.invoice_id)
            .subquery()
        )
        avg_time_val = db.scalar(select(func.avg(subq.c.total_ms)))

    avg_processing_time_ms = round(float(avg_time_val), 1) if avg_time_val else 0.0

    total_time_val = db.scalar(
        select(func.sum(Invoice.processed_ms)).where(Invoice.processed_ms.is_not(None))
    )
    if total_time_val is None:
        total_time_val = db.scalar(select(func.sum(AgentRun.duration_ms)))

    total_processing_time_ms = int(total_time_val or 0)

    # Estimated hours saved: manual handling ~15 min (0.25h) vs system processing
    manual_hours = processed_invoices * 0.25
    system_hours = total_processing_time_ms / 3_600_000.0
    estimated_hours_saved = max(0.0, round(manual_hours - system_hours, 2))

    # Total AI cost
    cost_val = db.scalar(
        select(func.coalesce(func.sum(Invoice.cost_usd), Decimal(0)))
    )
    if cost_val is None or cost_val == 0:
        tokens_in = (
            db.scalar(select(func.coalesce(func.sum(AgentRun.tokens_in), 0))) or 0
        )
        tokens_out = (
            db.scalar(select(func.coalesce(func.sum(AgentRun.tokens_out), 0))) or 0
        )
        if tokens_in > 0 or tokens_out > 0 or processed_invoices > 0:
            doc_intel = Decimal("0.0100") * Decimal(processed_invoices)
            llm = (Decimal(tokens_in) * Decimal("0.00000015")) + (
                Decimal(tokens_out) * Decimal("0.00000060")
            )
            cost_val = round(doc_intel + llm, 4)
        else:
            cost_val = Decimal("0.0000")

    total_ai_cost_usd = Decimal(str(cost_val))

    # Decisions breakdown
    aprobar_count = (
        db.scalar(select(func.count(Invoice.id)).where(Invoice.decision == "APROBAR"))
        or 0
    )
    revision_count = (
        db.scalar(select(func.count(Invoice.id)).where(Invoice.decision == "REVISION"))
        or 0
    )
    rechazar_count = (
        db.scalar(select(func.count(Invoice.id)).where(Invoice.decision == "RECHAZAR"))
        or 0
    )
    pending_count = (
        db.scalar(
            select(func.count(Invoice.id)).where(
                or_(
                    Invoice.decision.is_(None),
                    Invoice.status.in_(["PENDING", "PROCESSING"]),
                )
            )
        )
        or 0
    )

    decisions_summary = DecisionBreakdown(
        aprobar=aprobar_count,
        revision=revision_count,
        rechazar=rechazar_count,
        pending=pending_count,
        total=total_invoices,
    )

    # Daily decisions
    day_expr = func.cast(Invoice.created_at, Date)
    daily_rows = db.execute(
        select(
            day_expr.label("day"),
            func.sum(case((Invoice.decision == "APROBAR", 1), else_=0)).label("aprobar"),
            func.sum(case((Invoice.decision == "REVISION", 1), else_=0)).label("revision"),
            func.sum(case((Invoice.decision == "RECHAZAR", 1), else_=0)).label("rechazar"),
            func.count(Invoice.id).label("total"),
        )
        .group_by(day_expr)
        .order_by(day_expr.asc())
    ).all()

    daily_decisions = [
        DailyDecisionPoint(
            date=row.day.isoformat() if hasattr(row.day, "isoformat") else str(row.day),
            aprobar=int(row.aprobar or 0),
            revision=int(row.revision or 0),
            rechazar=int(row.rechazar or 0),
            total=int(row.total or 0),
        )
        for row in daily_rows
    ]

    # Top findings
    total_findings_count = db.scalar(select(func.count(FindingRecord.id))) or 0
    finding_rows = db.execute(
        select(
            FindingRecord.code,
            FindingRecord.severity,
            func.count(FindingRecord.id).label("cnt"),
        )
        .group_by(FindingRecord.code, FindingRecord.severity)
        .order_by(desc("cnt"))
        .limit(10)
    ).all()

    top_findings = [
        FindingMetricItem(
            code=row.code,
            label=FINDING_LABELS.get(row.code, row.code),
            severity=row.severity,
            count=int(row.cnt),
            percentage=(
                round((int(row.cnt) / total_findings_count) * 100.0, 1)
                if total_findings_count > 0
                else 0.0
            ),
        )
        for row in finding_rows
    ]

    return MetricsResponse(
        kpis=MetricsKPIs(
            total_invoices=total_invoices,
            processed_invoices=processed_invoices,
            auto_approved_count=auto_approved_count,
            auto_approval_rate_pct=auto_approval_rate_pct,
            avg_processing_time_ms=avg_processing_time_ms,
            total_processing_time_ms=total_processing_time_ms,
            estimated_hours_saved=estimated_hours_saved,
            total_ai_cost_usd=total_ai_cost_usd,
        ),
        decisions_summary=decisions_summary,
        daily_decisions=daily_decisions,
        top_findings=top_findings,
    )
