export type DecisionType = 'APROBAR' | 'REVISION' | 'RECHAZAR'
export type InvoiceStatus = 'PROCESSING' | 'PROCESSED' | 'ERROR'
export type FindingSeverity = 'INFO' | 'MEDIA' | 'ALTA' | 'CRITICA'

export interface InvoiceFindingSummary {
  id: string
  code: string
  severity: FindingSeverity
  message: string
}

export interface InvoiceListItem {
  id: string
  file_hash: string
  status: InvoiceStatus
  decision: DecisionType | null
  supplier_id: string | null
  supplier_name: string | null
  supplier_nit: string | null
  invoice_number: string
  issue_date: string | null
  total: number | string
  created_at: string
  processed_ms: number | null
  cost_usd: number | string | null
  findings: InvoiceFindingSummary[]
  has_bank_account_alert: boolean
}

export interface InvoiceListResponse {
  items: InvoiceListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface InvoiceFilters {
  status?: string
  decision?: string
  supplier?: string
  search?: string
  bank_account_alert?: boolean
  page?: number
  page_size?: number
}

export interface InvoiceLine {
  sku: string | null
  description: string
  quantity: number | string
  unit_price: number | string
  vat_rate: number | string
  line_subtotal: number | string
}

export interface BankAccount {
  bank: string
  account_type: 'Ahorros' | 'Corriente'
  number: string
}

export interface Finding {
  code: string
  severity: FindingSeverity
  message: string
  evidence: Record<string, unknown>
}

export interface ThreeWayMatchLine {
  sku: string | null
  description: string
  invoice_qty: number | string
  invoice_unit_price: number | string
  po_qty: number | string | null
  po_unit_price: number | string | null
  received_qty: number | string | null
  price_variance_pct: number | null
  status: 'MATCH' | 'PRICE_MISMATCH' | 'QTY_MISMATCH' | 'MISSING_PO_LINE' | 'NO_PO'
}

export interface PurchaseOrderDetailSummary {
  number: string
  date: string
  status: string
  lines_count: number
}

export interface InvoiceDetailResponse {
  id: string
  file_hash: string
  blob_url: string
  status: InvoiceStatus
  decision: DecisionType | null
  supplier_id: string | null
  supplier_name: string | null
  supplier_nit: string | null
  invoice_number: string
  issue_date: string | null
  due_date: string | null
  purchase_order_number: string | null
  currency: string
  subtotal: number | string
  vat_total: number | string
  total: number | string
  cufe: string | null
  bank_account: BankAccount | null
  lines: InvoiceLine[]
  field_confidence: Record<string, number>
  findings: Finding[]
  explanation: string | null
  supplier_email_draft: string | null
  three_way_match: ThreeWayMatchLine[]
  purchase_order: PurchaseOrderDetailSummary | null
  created_at: string
  processed_ms: number | null
  cost_usd: number | string | null
  has_bank_account_alert: boolean
}

export interface InvoiceFileResponse {
  url: string
  file_hash: string
  expires_in_seconds: number
}

export interface AgentRunItem {
  id: string
  invoice_id: string
  node: string
  started_at: string
  duration_ms: number
  tokens_in: number | null
  tokens_out: number | null
  output: Record<string, unknown> | null
}

export interface InvoiceTraceResponse {
  invoice_id: string
  status: InvoiceStatus
  decision: DecisionType | null
  total_duration_ms: number
  total_tokens_in: number
  total_tokens_out: number
  cost_usd: number | string | null
  runs: AgentRunItem[]
}

export type ReviewAction = 'APROBAR' | 'RECHAZAR'

export interface ReviewPayload {
  action: ReviewAction
  comment?: string | null
  reviewer?: string
}

export interface ReviewResponse {
  id: string
  invoice_id: string
  reviewer: string
  action: ReviewAction
  comment: string | null
  created_at: string
  previous_decision: string | null
  new_decision: string
}


