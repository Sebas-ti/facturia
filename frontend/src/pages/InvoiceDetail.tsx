import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import { AgentTraceView } from '../components/AgentTraceView'
import {
  fetchInvoiceDetail,
  fetchInvoiceFile,
  fetchInvoiceTrace,
  invoicePdfStreamUrl,
} from '../lib/api'
import type { DecisionType, FindingSeverity, ThreeWayMatchLine } from '../types/invoices'

function formatCop(amount: number | string | null | undefined): string {
  if (amount === null || amount === undefined) return '—'
  const num = typeof amount === 'string' ? parseFloat(amount) : amount
  if (isNaN(num)) return '—'
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  }).format(num)
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—'
  try {
    const parts = dateStr.split('T')[0].split('-').map(Number)
    if (parts.length === 3) {
      const [year, month, day] = parts
      const d = new Date(year, month - 1, day)
      return d.toLocaleDateString('es-CO', { year: 'numeric', month: 'short', day: 'numeric' })
    }
    return dateStr
  } catch {
    return dateStr
  }
}

function DecisionBadge({ decision, status }: { decision: DecisionType | null; status: string }) {
  if (status === 'PROCESSING') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-300">
        <span className="h-2 w-2 animate-pulse rounded-full bg-blue-500" />
        En procesamiento
      </span>
    )
  }

  if (status === 'ERROR') {
    return (
      <span className="inline-flex items-center rounded-full border border-slate-300 bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
        Error en pipeline
      </span>
    )
  }

  switch (decision) {
    case 'APROBAR':
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300">
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
          </svg>
          APROBADA
        </span>
      )
    case 'REVISION':
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300">
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          REQUIERE REVISIÓN
        </span>
      )
    case 'RECHAZAR':
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-300">
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
          </svg>
          RECHAZADA
        </span>
      )
    default:
      return (
        <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
          Pendiente
        </span>
      )
  }
}

function SeverityBadge({ severity }: { severity: FindingSeverity }) {
  const styles: Record<FindingSeverity, string> = {
    CRITICA: 'bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950/70 dark:text-rose-300 dark:border-rose-800',
    ALTA: 'bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-950/70 dark:text-orange-300 dark:border-orange-800',
    MEDIA: 'bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950/70 dark:text-amber-300 dark:border-amber-800',
    INFO: 'bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950/70 dark:text-blue-300 dark:border-blue-800',
  }
  return (
    <span className={`rounded border px-2 py-0.5 text-xs font-semibold uppercase ${styles[severity] || styles.INFO}`}>
      {severity}
    </span>
  )
}

function MatchStatusBadge({ status }: { status: ThreeWayMatchLine['status'] }) {
  switch (status) {
    case 'MATCH':
      return (
        <span className="inline-flex items-center rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300">
          Coincide
        </span>
      )
    case 'PRICE_MISMATCH':
      return (
        <span className="inline-flex items-center rounded-md bg-rose-50 px-2 py-0.5 text-xs font-medium text-rose-700 dark:bg-rose-950/50 dark:text-rose-300">
          Discrepancia precio &gt; 2%
        </span>
      )
    case 'QTY_MISMATCH':
      return (
        <span className="inline-flex items-center rounded-md bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-950/50 dark:text-amber-300">
          Excede recepción
        </span>
      )
    case 'MISSING_PO_LINE':
      return (
        <span className="inline-flex items-center rounded-md bg-orange-50 px-2 py-0.5 text-xs font-medium text-orange-700 dark:bg-orange-950/50 dark:text-orange-300">
          Línea no en OC
        </span>
      )
    case 'NO_PO':
      return (
        <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-400">
          Sin OC
        </span>
      )
  }
}

export function InvoiceDetail() {
  const { id } = useParams<{ id: string }>()
  const [copiedEmail, setCopiedEmail] = useState(false)
  const [copiedCufe, setCopiedCufe] = useState(false)
  const [activeTab, setActiveTab] = useState<'detail' | 'trace'>('detail')

  const { data: invoice, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['invoice-detail', id],
    queryFn: () => (id ? fetchInvoiceDetail(id) : Promise.reject(new Error('ID no válido'))),
    enabled: Boolean(id),
  })

  const { data: traceData, isLoading: isTraceLoading } = useQuery({
    queryKey: ['invoice-trace', id],
    queryFn: () => (id ? fetchInvoiceTrace(id) : null),
    enabled: Boolean(id),
  })

  const handleOpenPdfSas = async () => {
    if (!id) return
    try {
      const fileData = await fetchInvoiceFile(id)
      window.open(fileData.url, '_blank', 'noopener,noreferrer')
    } catch {
      window.open(invoicePdfStreamUrl(id), '_blank', 'noopener,noreferrer')
    }
  }

  const handleCopyEmail = () => {
    if (invoice?.supplier_email_draft) {
      navigator.clipboard.writeText(invoice.supplier_email_draft)
      setCopiedEmail(true)
      setTimeout(() => setCopiedEmail(false), 2000)
    }
  }

  const handleCopyCufe = () => {
    if (invoice?.cufe) {
      navigator.clipboard.writeText(invoice.cufe)
      setCopiedCufe(true)
      setTimeout(() => setCopiedCufe(false), 2000)
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
          <span className="h-6 w-6 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
          Cargando detalle de la factura...
        </div>
      </div>
    )
  }

  if (isError || !invoice) {
    return (
      <div className="mx-auto max-w-xl p-8 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-rose-100 text-rose-600 dark:bg-rose-950 dark:text-rose-400">
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h2 className="mt-4 text-lg font-bold text-slate-900 dark:text-slate-100">
          Factura no encontrada
        </h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          {error instanceof Error ? error.message : 'No se pudo cargar la información de la factura solicitada.'}
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <button
            type="button"
            onClick={() => refetch()}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            Reintentar
          </button>
          <Link
            to="/invoices"
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 dark:bg-brand-500"
          >
            Volver a la bandeja
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Top Navigation Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Link
          to="/invoices"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Volver a la bandeja
        </Link>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleOpenPdfSas}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
            Abrir PDF completo
          </button>
          {invoice.decision === 'REVISION' && (
            <Link
              to="/review"
              className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-amber-700"
            >
              Ir a cola de revisión
            </Link>
          )}
        </div>
      </div>

      {/* Fraud Alert Banner */}
      {invoice.has_bank_account_alert && (
        <div className="flex items-start gap-3 rounded-xl border border-rose-300 bg-rose-50 p-4 dark:border-rose-900 dark:bg-rose-950/40">
          <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-rose-200 text-rose-700 dark:bg-rose-900 dark:text-rose-300">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <h2 className="text-sm font-bold text-rose-900 dark:text-rose-200">
              ALERTA CRÍTICA: Cuenta bancaria impresa difiere del maestro
            </h2>
            <p className="mt-1 text-xs text-rose-800 dark:text-rose-300">
              La cuenta bancaria detectada en el PDF no coincide con la registrada para este proveedor. No autorice el pago sin verificar directamente con el proveedor a través de un canal seguro fuera de banda.
            </p>
          </div>
        </div>
      )}

      {/* Main Split Layout: Left PDF, Right Details */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left Pane: PDF Viewer (5 cols) */}
        <div className="lg:col-span-5">
          <div className="sticky top-6 space-y-3">
            <div className="flex items-center justify-between rounded-t-xl border border-b-0 border-slate-200 bg-slate-100 px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
              <span className="text-xs font-bold tracking-wider text-slate-700 uppercase dark:text-slate-300">
                Documento original (PDF)
              </span>
              <span className="font-mono text-[11px] text-slate-500 dark:text-slate-400">
                SHA: {invoice.file_hash ? invoice.file_hash.slice(0, 10) + '...' : '—'}
              </span>
            </div>
            <div className="overflow-hidden rounded-b-xl border border-slate-200 bg-slate-900 dark:border-slate-800">
              {id ? (
                <iframe
                  src={invoicePdfStreamUrl(id)}
                  title={`Factura ${invoice.invoice_number}`}
                  className="h-[650px] w-full border-0 bg-slate-100 dark:bg-slate-900"
                />
              ) : null}
            </div>
          </div>
        </div>

        {/* Right Pane: Analysis & Structured Data (7 cols) */}
        <div className="space-y-6 lg:col-span-7">
          {/* Header Card */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900/50">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <span className="text-xs font-semibold text-brand-600 uppercase dark:text-brand-400">
                  Detalle de Factura
                </span>
                <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                  {invoice.invoice_number || 'PENDIENTE'}
                </h1>
              </div>
              <DecisionBadge decision={invoice.decision} status={invoice.status} />
            </div>

            <div className="mt-4 grid grid-cols-2 gap-4 border-t border-slate-100 pt-4 text-sm sm:grid-cols-3 dark:border-slate-800">
              <div>
                <dt className="text-xs text-slate-500 dark:text-slate-400">Proveedor</dt>
                <dd className="font-medium text-slate-900 dark:text-slate-100">
                  {invoice.supplier_name || 'Desconocido'}
                </dd>
                {invoice.supplier_nit && (
                  <span className="text-xs text-slate-500">NIT: {invoice.supplier_nit}</span>
                )}
              </div>
              <div>
                <dt className="text-xs text-slate-500 dark:text-slate-400">Fecha de emisión</dt>
                <dd className="font-medium text-slate-900 dark:text-slate-100">
                  {formatDate(invoice.issue_date)}
                </dd>
                {invoice.due_date && (
                  <span className="text-xs text-slate-500">Vence: {formatDate(invoice.due_date)}</span>
                )}
              </div>
              <div>
                <dt className="text-xs text-slate-500 dark:text-slate-400">Total a pagar</dt>
                <dd className="text-base font-bold text-slate-900 dark:text-slate-100">
                  {formatCop(invoice.total)}
                </dd>
                <span className="text-xs text-slate-500">{invoice.currency}</span>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800">
            <button
              type="button"
              onClick={() => setActiveTab('detail')}
              className={`inline-flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-semibold transition-colors ${
                activeTab === 'detail'
                  ? 'border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400'
                  : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Detalle & Análisis
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('trace')}
              className={`inline-flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-semibold transition-colors ${
                activeTab === 'trace'
                  ? 'border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400'
                  : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Traza de Agentes
              {traceData?.runs && (
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {traceData.runs.length} pasos
                </span>
              )}
            </button>
          </div>

          {activeTab === 'detail' ? (
            <>
              {/* AI Decision Explanation */}
              {invoice.explanation && (
                <div className="rounded-xl border border-brand-200 bg-brand-50/60 p-5 shadow-xs dark:border-brand-900/50 dark:bg-brand-950/20">
              <div className="flex items-center gap-2 text-sm font-semibold text-brand-900 dark:text-brand-300">
                <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
                </svg>
                Explicación del Agente Decisor
              </div>
              <p className="mt-2 text-sm leading-relaxed text-brand-950 dark:text-brand-200">
                {invoice.explanation}
              </p>
              <div className="mt-2 text-[11px] text-brand-700/80 dark:text-brand-400/80">
                Decisión evaluada con base en la matriz de reglas deterministas (spec §4.2).
              </div>
            </div>
          )}

          {/* Supplier Email Draft (if rejected) */}
          {invoice.supplier_email_draft && (
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900/50">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  Borrador de comunicación al proveedor
                </h3>
                <button
                  type="button"
                  onClick={handleCopyEmail}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                >
                  {copiedEmail ? '✓ Copiado' : 'Copiar texto'}
                </button>
              </div>
              <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-4 text-xs font-mono text-slate-800 whitespace-pre-wrap dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200">
                {invoice.supplier_email_draft}
              </div>
            </div>
          )}

          {/* Findings with Evidence */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900/50">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Hallazgos y Reglas Evaluadas ({invoice.findings.length})
            </h3>
            {invoice.findings.length === 0 ? (
              <div className="mt-3 flex items-center gap-2 rounded-lg bg-emerald-50 p-3 text-xs text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Sin hallazgos adversos. Todas las reglas aritméticas, NIT, CUFE y matching pasaron con éxito.
              </div>
            ) : (
              <div className="mt-3 divide-y divide-slate-100 dark:divide-slate-800">
                {invoice.findings.map((finding) => (
                  <div key={finding.code} className="py-3 first:pt-0 last:pb-0">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <SeverityBadge severity={finding.severity} />
                        <span className="font-mono text-xs font-bold text-slate-900 dark:text-slate-100">
                          {finding.code}
                        </span>
                      </div>
                    </div>
                    <p className="mt-1 text-xs text-slate-700 dark:text-slate-300">
                      {finding.message}
                    </p>
                    {finding.evidence && Object.keys(finding.evidence).length > 0 && (
                      <div className="mt-2 rounded bg-slate-50 p-2 font-mono text-[11px] text-slate-600 dark:bg-slate-950 dark:text-slate-400">
                        <span className="font-semibold text-slate-500">Evidencia: </span>
                        {JSON.stringify(finding.evidence, null, 2)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Extraction Field Confidence Gauge */}
          {invoice.field_confidence && Object.keys(invoice.field_confidence).length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900/50">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Semáforo de Confianza de Extracción (OCR / Doc Intelligence)
              </h3>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                Umbral mínimo de aceptación: 80% (campos por debajo de 0.80 detienen a revisión humana).
              </p>
              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                {Object.entries(invoice.field_confidence).map(([field, score]) => {
                  const pct = Math.round(score * 100)
                  const isHigh = pct >= 80
                  return (
                    <div
                      key={field}
                      className={`rounded-lg border p-3 ${
                        isHigh
                          ? 'border-slate-200 bg-slate-50/50 dark:border-slate-800 dark:bg-slate-900/40'
                          : 'border-amber-300 bg-amber-50/50 dark:border-amber-900 dark:bg-amber-950/20'
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium text-slate-700 dark:text-slate-300 capitalize">
                          {field.replace(/_/g, ' ')}
                        </span>
                        <span
                          className={`font-mono font-bold ${
                            isHigh ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'
                          }`}
                        >
                          {pct}%
                        </span>
                      </div>
                      <div className="mt-2 h-1.5 w-full rounded-full bg-slate-200 dark:bg-slate-800">
                        <div
                          className={`h-1.5 rounded-full ${
                            isHigh ? 'bg-emerald-500' : 'bg-amber-500'
                          }`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* 3-Way Match Line Comparison */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900/50">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  Conciliación 3-Way Match (Factura vs. OC vs. Recepción)
                </h3>
                {invoice.purchase_order ? (
                  <p className="mt-0.5 text-xs text-slate-500">
                    Orden de compra: <span className="font-mono font-medium">{invoice.purchase_order.number}</span> ({invoice.purchase_order.status})
                  </p>
                ) : (
                  <p className="mt-0.5 text-xs text-amber-600 dark:text-amber-400">
                    Factura sin referencia válida a orden de compra
                  </p>
                )}
              </div>
            </div>

            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-200 bg-slate-50 text-slate-500 uppercase dark:border-slate-800 dark:bg-slate-900">
                  <tr>
                    <th className="py-2 pr-2 pl-3">SKU / Ítem</th>
                    <th className="px-2 py-2 text-right">Cant. Fact</th>
                    <th className="px-2 py-2 text-right">Cant. Recep</th>
                    <th className="px-2 py-2 text-right">Precio Fact</th>
                    <th className="px-2 py-2 text-right">Precio OC</th>
                    <th className="px-2 py-2 text-center">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {invoice.three_way_match.map((line, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                      <td className="py-2.5 pr-2 pl-3">
                        <div className="font-medium text-slate-900 dark:text-slate-100">
                          {line.sku || '—'}
                        </div>
                        <div className="text-[11px] text-slate-500 truncate max-w-xs">
                          {line.description}
                        </div>
                      </td>
                      <td className="px-2 py-2.5 text-right font-medium text-slate-900 dark:text-slate-100">
                        {line.invoice_qty}
                      </td>
                      <td className="px-2 py-2.5 text-right text-slate-700 dark:text-slate-300">
                        {line.received_qty ?? '—'}
                      </td>
                      <td className="px-2 py-2.5 text-right font-medium text-slate-900 dark:text-slate-100">
                        {formatCop(line.invoice_unit_price)}
                      </td>
                      <td className="px-2 py-2.5 text-right text-slate-700 dark:text-slate-300">
                        {line.po_unit_price !== null ? formatCop(line.po_unit_price) : '—'}
                      </td>
                      <td className="px-2 py-2.5 text-center">
                        <MatchStatusBadge status={line.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Bank Account & CUFE Details */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {/* Bank Account */}
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900/50">
              <h4 className="text-xs font-semibold text-slate-700 uppercase dark:text-slate-300">
                Cuenta Bancaria en Factura
              </h4>
              {invoice.bank_account ? (
                <div className="mt-2 space-y-1 text-xs text-slate-600 dark:text-slate-400">
                  <p><span className="font-medium text-slate-900 dark:text-slate-100">Banco:</span> {invoice.bank_account.bank}</p>
                  <p><span className="font-medium text-slate-900 dark:text-slate-100">Tipo:</span> {invoice.bank_account.account_type}</p>
                  <p><span className="font-medium text-slate-900 dark:text-slate-100">Número:</span> <span className="font-mono">{invoice.bank_account.number}</span></p>
                </div>
              ) : (
                <p className="mt-2 text-xs text-slate-400">No se detectó cuenta bancaria impresa.</p>
              )}
            </div>

            {/* CUFE */}
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900/50">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-slate-700 uppercase dark:text-slate-300">
                  CUFE (DIAN)
                </h4>
                {invoice.cufe && (
                  <button
                    type="button"
                    onClick={handleCopyCufe}
                    className="text-[11px] text-brand-600 hover:underline dark:text-brand-400"
                  >
                    {copiedCufe ? '✓ Copiado' : 'Copiar'}
                  </button>
                )}
              </div>
              {invoice.cufe ? (
                <p className="mt-2 font-mono text-[11px] text-slate-600 break-all dark:text-slate-400">
                  {invoice.cufe}
                </p>
              ) : (
                <p className="mt-2 text-xs text-slate-400">CUFE no registrado o no detectado.</p>
              )}
              </div>
            </div>
          </>
          ) : (
            <AgentTraceView
              trace={traceData}
              isLoading={isTraceLoading}
              invoiceId={id || ''}
              decision={invoice.decision}
            />
          )}
        </div>
      </div>
    </div>
  )
}

