import type { EvalReportsResponse } from '../types/evals'
import type {
  InvoiceDetailResponse,
  InvoiceFileResponse,
  InvoiceFilters,
  InvoiceListResponse,
  InvoiceTraceResponse,
  ReviewPayload,
  ReviewResponse,
} from '../types/invoices'
import type { PurchaseOrderItem, SupplierItem } from '../types/masterData'
import type { MetricsResponse } from '../types/metrics'

// '/api' works when a reverse proxy sits in front of both (Vite's dev proxy,
// or nginx.conf in Docker Compose). Static Web Apps + Container Apps
// (infra/main.bicep) are separate origins with no such proxy, so that build
// sets VITE_API_BASE_URL to the Container App's full URL instead.
const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api'

// Same shared secret the Power Automate flow uses (docs/spec.md §6) — there's
// no web login yet, so this endpoint accepts either caller with this one key.
const API_KEY = import.meta.env.VITE_API_KEY as string | undefined

export async function uploadInvoice(file: File): Promise<{ invoiceId: string }> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/invoices`, {
    method: 'POST',
    headers: API_KEY ? { 'X-API-Key': API_KEY } : undefined,
    body: formData,
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? `Error al subir la factura (${response.status})`)
  }

  const data = (await response.json()) as { invoice_id: string }
  return { invoiceId: data.invoice_id }
}

export async function fetchInvoices(filters: InvoiceFilters = {}): Promise<InvoiceListResponse> {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.decision) params.set('decision', filters.decision)
  if (filters.supplier) params.set('supplier', filters.supplier)
  if (filters.search) params.set('search', filters.search)
  if (filters.bank_account_alert !== undefined) {
    params.set('bank_account_alert', String(filters.bank_account_alert))
  }
  if (filters.page) params.set('page', String(filters.page))
  if (filters.page_size) params.set('page_size', String(filters.page_size))

  const queryString = params.toString()
  const url = queryString ? `${API_BASE}/invoices?${queryString}` : `${API_BASE}/invoices`

  const response = await fetch(url)
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? `Error al obtener facturas (${response.status})`)
  }

  return (await response.json()) as InvoiceListResponse
}

export async function fetchInvoiceDetail(invoiceId: string): Promise<InvoiceDetailResponse> {
  const response = await fetch(`${API_BASE}/invoices/${invoiceId}`)
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? `Error al obtener detalle de la factura (${response.status})`)
  }

  return (await response.json()) as InvoiceDetailResponse
}

export async function fetchInvoiceFile(invoiceId: string): Promise<InvoiceFileResponse> {
  const response = await fetch(`${API_BASE}/invoices/${invoiceId}/file`)
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? `Error al obtener URL del archivo (${response.status})`)
  }

  return (await response.json()) as InvoiceFileResponse
}

export function invoicePdfStreamUrl(invoiceId: string): string {
  return `${API_BASE}/invoices/${invoiceId}/file?stream=true`
}

export function invoiceEventsUrl(invoiceId: string): string {
  return `${API_BASE}/invoices/${invoiceId}/events`
}

export async function fetchInvoiceTrace(invoiceId: string): Promise<InvoiceTraceResponse> {
  const response = await fetch(`${API_BASE}/invoices/${invoiceId}/trace`)
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? `Error al obtener la traza de la factura (${response.status})`)
  }

  return (await response.json()) as InvoiceTraceResponse
}

export async function reviewInvoice(
  invoiceId: string,
  payload: ReviewPayload,
): Promise<ReviewResponse> {
  const response = await fetch(`${API_BASE}/invoices/${invoiceId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? `Error al registrar revisión de la factura (${response.status})`)
  }

  return (await response.json()) as ReviewResponse
}

export async function fetchMetrics(): Promise<MetricsResponse> {
  const response = await fetch(`${API_BASE}/metrics`)
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? `Error al obtener métricas del sistema (${response.status})`)
  }

  return (await response.json()) as MetricsResponse
}

export async function fetchEvalReports(reportId?: string): Promise<EvalReportsResponse> {
  const url = reportId ? `${API_BASE}/evals?report_id=${encodeURIComponent(reportId)}` : `${API_BASE}/evals`
  const response = await fetch(url)
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? `Error al obtener reportes de evaluación (${response.status})`)
  }

  return (await response.json()) as EvalReportsResponse
}

export async function fetchSuppliers(params?: {
  search?: string
  status?: string
}): Promise<SupplierItem[]> {
  const q = new URLSearchParams()
  if (params?.search) q.set('search', params.search)
  if (params?.status) q.set('status', params.status)
  const qs = q.toString()
  const response = await fetch(`${API_BASE}/suppliers${qs ? `?${qs}` : ''}`)
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? `Error al obtener proveedores (${response.status})`)
  }
  return (await response.json()) as SupplierItem[]
}

export async function fetchPurchaseOrders(params?: {
  number?: string
  supplier_nit?: string
  status?: string
}): Promise<PurchaseOrderItem[]> {
  const q = new URLSearchParams()
  if (params?.number) q.set('number', params.number)
  if (params?.supplier_nit) q.set('supplier_nit', params.supplier_nit)
  if (params?.status) q.set('status', params.status)
  const qs = q.toString()
  const response = await fetch(`${API_BASE}/purchase-orders${qs ? `?${qs}` : ''}`)
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? `Error al obtener órdenes de compra (${response.status})`)
  }
  return (await response.json()) as PurchaseOrderItem[]
}

export async function fetchPurchaseOrder(numberOrId: string): Promise<PurchaseOrderItem> {
  const response = await fetch(`${API_BASE}/purchase-orders/${encodeURIComponent(numberOrId)}`)
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? `Error al obtener la orden de compra (${response.status})`)
  }
  return (await response.json()) as PurchaseOrderItem
}


