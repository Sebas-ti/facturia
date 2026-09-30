export interface MetricsKPIs {
  total_invoices: number
  processed_invoices: number
  auto_approved_count: number
  auto_approval_rate_pct: number
  avg_processing_time_ms: number
  total_processing_time_ms: number
  estimated_hours_saved: number
  total_ai_cost_usd: number | string
}

export interface DecisionBreakdown {
  aprobar: number
  revision: number
  rechazar: number
  pending: number
  total: number
}

export interface DailyDecisionPoint {
  date: string
  aprobar: number
  revision: number
  rechazar: number
  total: number
}

export interface FindingMetricItem {
  code: string
  label: string
  severity: 'INFO' | 'MEDIA' | 'ALTA' | 'CRITICA'
  count: number
  percentage: number
}

export interface MetricsResponse {
  kpis: MetricsKPIs
  decisions_summary: DecisionBreakdown
  daily_decisions: DailyDecisionPoint[]
  top_findings: FindingMetricItem[]
}
