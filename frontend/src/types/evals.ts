export interface EvalReportSummary {
  id: string
  filename: string
  title: string
  generated_at: string
  mode: 'mock' | 'live' | string
  total_cases: number
  successful_cases: number
  accuracy_pct: number
  is_latest: boolean
}

export interface FieldAccuracyItem {
  field: string
  precision_pct: number
  hits: number
  total: number
}

export interface FindingAccuracyItem {
  code: string
  precision_pct: number
  recall_pct: number
  tp: number
  fp: number
  fn: number
}

export interface ConfusionMatrixRow {
  expected: string
  aprobar: number
  revision: number
  rechazar: number
}

export interface ConfusionMatrixData {
  labels: string[]
  rows: ConfusionMatrixRow[]
  accuracy_pct: number
  correct: number
  total: number
}

export interface InvoiceCaseResult {
  invoice_id: string
  status: 'OK' | 'FALLA' | string
  detail: string
}

export interface EvalReportDetail {
  id: string
  filename: string
  title: string
  generated_at: string
  mode: 'mock' | 'live' | string
  summary: string
  overall_accuracy_pct: number
  total_cases: number
  successful_cases: number
  raw_markdown: string
  extraction_accuracy: FieldAccuracyItem[]
  findings_accuracy: FindingAccuracyItem[]
  confusion_matrix: ConfusionMatrixData
  invoice_cases: InvoiceCaseResult[]
}

export interface EvalReportsResponse {
  reports: EvalReportSummary[]
  selected: EvalReportDetail
}
