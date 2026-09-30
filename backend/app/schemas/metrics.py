from decimal import Decimal

from pydantic import BaseModel


class MetricsKPIs(BaseModel):
    total_invoices: int
    processed_invoices: int
    auto_approved_count: int
    auto_approval_rate_pct: float
    avg_processing_time_ms: float
    total_processing_time_ms: int
    estimated_hours_saved: float
    total_ai_cost_usd: Decimal


class DecisionBreakdown(BaseModel):
    aprobar: int
    revision: int
    rechazar: int
    pending: int
    total: int


class DailyDecisionPoint(BaseModel):
    date: str
    aprobar: int
    revision: int
    rechazar: int
    total: int


class FindingMetricItem(BaseModel):
    code: str
    label: str
    severity: str
    count: int
    percentage: float


class MetricsResponse(BaseModel):
    kpis: MetricsKPIs
    decisions_summary: DecisionBreakdown
    daily_decisions: list[DailyDecisionPoint]
    top_findings: list[FindingMetricItem]
