import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { fetchInvoiceDetail, fetchInvoices, reviewInvoice } from '../lib/api'
import type { FindingSeverity, InvoiceListItem, ReviewAction } from '../types/invoices'

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

function SeverityBadge({ severity }: { severity: FindingSeverity }) {
  const styles: Record<FindingSeverity, string> = {
    CRITICA: 'bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950/70 dark:text-rose-300 dark:border-rose-800',
    ALTA: 'bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-950/70 dark:text-orange-300 dark:border-orange-800',
    MEDIA: 'bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950/70 dark:text-amber-300 dark:border-amber-800',
    INFO: 'bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950/70 dark:text-blue-300 dark:border-blue-800',
  }
  return (
    <span className={`rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase ${styles[severity] || styles.INFO}`}>
      {severity}
    </span>
  )
}

export function Review() {
  const queryClient = useQueryClient()
  const [userSelectedId, setUserSelectedId] = useState<string | null>(null)
  const [comment, setComment] = useState('')
  const [reviewer, setReviewer] = useState('analista@facturia.co')
  const [feedback, setFeedback] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  // Fetch queue of invoices in REVISION
  const { data: queueData, isLoading: isLoadingQueue, refetch } = useQuery({
    queryKey: ['invoices-review-queue'],
    queryFn: () => fetchInvoices({ decision: 'REVISION', page_size: 50 }),
  })

  const queueItems = queueData?.items ?? []

  // Derive active selection without side effects
  const activeItem =
    queueItems.find((inv) => inv.id === userSelectedId) ||
    queueItems.find((inv) => inv.has_bank_account_alert) ||
    queueItems[0] ||
    null
  const selectedId = activeItem?.id ?? null

  // Fetch detailed info of selected invoice
  const { data: selectedInvoice, isLoading: isLoadingDetail } = useQuery({
    queryKey: ['invoice-detail', selectedId],
    queryFn: () => (selectedId ? fetchInvoiceDetail(selectedId) : null),
    enabled: Boolean(selectedId),
  })

  // Review mutation
  const reviewMutation = useMutation({
    mutationFn: ({ invoiceId, action }: { invoiceId: string; action: ReviewAction }) =>
      reviewInvoice(invoiceId, {
        action,
        comment: comment.trim() || null,
        reviewer: reviewer.trim() || 'analista@facturia.co',
      }),
    onSuccess: (data, variables) => {
      const invNumber = selectedInvoice?.invoice_number || variables.invoiceId.slice(0, 8)
      setFeedback({
        message: `Factura ${invNumber} ${data.action === 'APROBAR' ? 'aprobada' : 'rechazada'} exitosamente.`,
        type: 'success',
      })
      setComment('')
      queryClient.invalidateQueries({ queryKey: ['invoices-review-queue'] })
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
      queryClient.invalidateQueries({ queryKey: ['invoice-detail', variables.invoiceId] })
      queryClient.invalidateQueries({ queryKey: ['invoice-trace', variables.invoiceId] })

      setTimeout(() => setFeedback(null), 4000)
    },
    onError: (err) => {
      setFeedback({
        message: err instanceof Error ? err.message : 'Error al registrar la revisión.',
        type: 'error',
      })
    },
  })

  const handleAction = (action: ReviewAction) => {
    if (!selectedId) return
    reviewMutation.mutate({ invoiceId: selectedId, action })
  }

  const bankAlertCount = queueItems.filter((i) => i.has_bank_account_alert).length

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <span className="text-xs font-semibold text-brand-600 uppercase dark:text-brand-400">
            Human-in-the-Loop
          </span>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Cola de Revisión
          </h1>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Facturas pausadas por el agente de decisión para validación humana antes de autorizar el pago.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300">
            <span className="h-2 w-2 rounded-full bg-amber-500" />
            {queueItems.length} en espera
          </span>
          <button
            type="button"
            onClick={() => refetch()}
            className="rounded-lg border border-slate-300 bg-white p-1.5 text-xs text-slate-600 shadow-xs hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
            title="Refrescar cola"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </div>

      {/* Fraud Alert Notification for the whole queue */}
      {bankAlertCount > 0 && (
        <div className="flex items-start gap-3 rounded-xl border border-rose-300 bg-rose-50 p-4 dark:border-rose-900 dark:bg-rose-950/40">
          <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-rose-200 text-rose-700 dark:bg-rose-900 dark:text-rose-300">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <h2 className="text-sm font-bold text-rose-900 dark:text-rose-200">
              ALERTA DE SEGURIDAD: {bankAlertCount} factura(s) con posible suplantación bancaria
            </h2>
            <p className="mt-0.5 text-xs text-rose-800 dark:text-rose-300">
              Se detectó discrepancia entre la cuenta bancaria impresa en el documento y la cuenta registrada en el maestro. Las facturas afectadas se muestran al tope con máxima prioridad.
            </p>
          </div>
        </div>
      )}

      {/* Success / Error Feedback Toast */}
      {feedback && (
        <div
          className={`flex items-center justify-between rounded-xl border p-4 text-xs font-semibold shadow-xs ${
            feedback.type === 'success'
              ? 'border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-200'
              : 'border-rose-300 bg-rose-50 text-rose-900 dark:border-rose-900 dark:bg-rose-950/60 dark:text-rose-200'
          }`}
        >
          <span>{feedback.message}</span>
          <button
            type="button"
            onClick={() => setFeedback(null)}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
          >
            ✕
          </button>
        </div>
      )}

      {/* Empty State */}
      {!isLoadingQueue && queueItems.length === 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center shadow-xs dark:border-slate-800 dark:bg-slate-900/50">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400">
            <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="mt-4 text-lg font-bold text-slate-900 dark:text-slate-100">
            ¡Cola de revisión al día!
          </h2>
          <p className="mx-auto mt-1 max-w-md text-xs text-slate-500 dark:text-slate-400">
            No hay facturas pendientes en estado REVISION. Todas las excepciones han sido resueltas o las facturas recibidas fueron aprobadas/rechazadas automáticamente.
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <Link
              to="/invoices"
              className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Ver todas las facturas
            </Link>
            <Link
              to="/upload"
              className="rounded-lg bg-brand-600 px-4 py-2 text-xs font-semibold text-white hover:bg-brand-700 dark:bg-brand-500"
            >
              Subir nueva factura
            </Link>
          </div>
        </div>
      )}

      {/* Main Two-Column Layout */}
      {queueItems.length > 0 && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Left Column: Queue List (5 cols) */}
          <div className="space-y-3 lg:col-span-5">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase dark:text-slate-400">
              <span>Facturas pendientes ({queueItems.length})</span>
              <span>Prioridad</span>
            </div>

            <div className="space-y-2.5 max-h-[750px] overflow-y-auto pr-1">
              {queueItems.map((item: InvoiceListItem) => {
                const isSelected = item.id === selectedId
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setUserSelectedId(item.id)}
                    className={`w-full text-left rounded-xl border p-4 transition-all ${
                      isSelected
                        ? 'border-brand-500 bg-white ring-2 ring-brand-500/20 shadow-md dark:border-brand-400 dark:bg-slate-900'
                        : 'border-slate-200 bg-white/70 hover:border-slate-300 hover:bg-white shadow-2xs dark:border-slate-800 dark:bg-slate-900/40 dark:hover:bg-slate-900'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-900 dark:text-slate-100">
                            {item.invoice_number || 'PENDIENTE'}
                          </span>
                          {item.has_bank_account_alert && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-rose-100 px-2 py-0.5 text-[10px] font-bold text-rose-700 dark:bg-rose-950 dark:text-rose-300">
                              <span className="h-1.5 w-1.5 animate-ping rounded-full bg-rose-500" />
                              ALERTA FRAUDE
                            </span>
                          )}
                        </div>
                        <p className="mt-1 text-xs font-medium text-slate-700 dark:text-slate-300 truncate max-w-[240px]">
                          {item.supplier_name || 'Proveedor desconocido'}
                        </p>
                      </div>

                      <div className="text-right">
                        <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                          {formatCop(item.total)}
                        </span>
                        <p className="mt-1 text-[11px] text-slate-500">
                          {formatDate(item.issue_date || item.created_at)}
                        </p>
                      </div>
                    </div>

                    {/* Findings chips preview */}
                    {item.findings.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1 border-t border-slate-100 pt-2 dark:border-slate-800/80">
                        {item.findings.map((f, idx) => (
                          <SeverityBadge key={idx} severity={f.severity} />
                        ))}
                      </div>
                    )}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Right Column: Review Workspace (7 cols) */}
          <div className="space-y-5 lg:col-span-7">
            {isLoadingDetail && (
              <div className="flex h-96 items-center justify-center rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900/50">
                <div className="flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
                  <span className="h-5 w-5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
                  Cargando información para revisión...
                </div>
              </div>
            )}

            {!isLoadingDetail && selectedInvoice && (
              <>
                {/* Selected Invoice Header Card */}
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900/50">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <span className="text-xs font-semibold text-amber-600 uppercase dark:text-amber-400">
                        Pausada para Revisión
                      </span>
                      <h2 className="mt-0.5 text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                        {selectedInvoice.invoice_number}
                      </h2>
                    </div>

                    <Link
                      to={`/invoices/${selectedInvoice.id}`}
                      className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand-600 hover:text-brand-700 dark:text-brand-400"
                    >
                      Ver Detalle Completo y PDF
                      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </Link>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-4 border-t border-slate-100 pt-4 text-xs sm:grid-cols-3 dark:border-slate-800">
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">Proveedor</span>
                      <p className="mt-0.5 font-bold text-slate-900 dark:text-slate-100">
                        {selectedInvoice.supplier_name || 'Desconocido'}
                      </p>
                      {selectedInvoice.supplier_nit && (
                        <p className="text-slate-500">NIT: {selectedInvoice.supplier_nit}</p>
                      )}
                    </div>
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">Total a pagar</span>
                      <p className="mt-0.5 text-sm font-bold text-slate-900 dark:text-slate-100">
                        {formatCop(selectedInvoice.total)}
                      </p>
                      <p className="text-slate-500">{selectedInvoice.currency}</p>
                    </div>
                    <div>
                      <span className="text-slate-500 dark:text-slate-400">Orden de compra</span>
                      <p className="mt-0.5 font-mono font-medium text-slate-900 dark:text-slate-100">
                        {selectedInvoice.purchase_order_number || 'Sin OC referenciada'}
                      </p>
                      <p className="text-slate-500">Emisión: {formatDate(selectedInvoice.issue_date)}</p>
                    </div>
                  </div>
                </div>

                {/* Specific Critical Bank Alert Banner */}
                {selectedInvoice.has_bank_account_alert && (
                  <div className="rounded-xl border border-rose-300 bg-rose-50 p-4 dark:border-rose-900 dark:bg-rose-950/40">
                    <div className="flex items-center gap-2 text-xs font-bold text-rose-900 uppercase dark:text-rose-200">
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      Alerta Crítica: Cuenta Bancaria No Coincide
                    </div>
                    <p className="mt-1 text-xs text-rose-800 dark:text-rose-300">
                      La cuenta impresa detectada es:{' '}
                      <span className="font-mono font-bold">
                        {selectedInvoice.bank_account
                          ? `${selectedInvoice.bank_account.bank} ${selectedInvoice.bank_account.account_type} ${selectedInvoice.bank_account.number}`
                          : 'No especificada'}
                      </span>.
                      Se recomienda rechazar o verificar con el proveedor antes de aprobar.
                    </p>
                  </div>
                )}

                {/* AI Explanation */}
                {selectedInvoice.explanation && (
                  <div className="rounded-xl border border-brand-200 bg-brand-50/60 p-5 shadow-xs dark:border-brand-900/50 dark:bg-brand-950/20">
                    <div className="flex items-center gap-2 text-xs font-bold text-brand-900 uppercase tracking-wider dark:text-brand-300">
                      <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
                      </svg>
                      Motivo de Revisión (Explicador IA)
                    </div>
                    <p className="mt-2 text-xs leading-relaxed text-brand-950 dark:text-brand-200">
                      {selectedInvoice.explanation}
                    </p>
                  </div>
                )}

                {/* Findings List */}
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900/50">
                  <h3 className="text-xs font-bold tracking-wider text-slate-700 uppercase dark:text-slate-300">
                    Hallazgos Detectados ({selectedInvoice.findings.length})
                  </h3>
                  <div className="mt-3 space-y-2">
                    {selectedInvoice.findings.map((f, idx) => (
                      <div
                        key={idx}
                        className="rounded-lg border border-slate-100 bg-slate-50/60 p-3 text-xs dark:border-slate-800 dark:bg-slate-900/40"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono font-bold text-slate-900 dark:text-slate-100">
                            {f.code}
                          </span>
                          <SeverityBadge severity={f.severity} />
                        </div>
                        <p className="mt-1 text-slate-600 dark:text-slate-400">
                          {f.message}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Human Review Decision Form */}
                <div className="rounded-xl border border-slate-300 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    Resolución del Analista
                  </h3>
                  <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                    Al confirmar, el grafo LangGraph continuará desde su punto de interrupción y se actualizará la decisión en la base de datos.
                  </p>

                  <div className="mt-4 space-y-4">
                    <div>
                      <label htmlFor="reviewer" className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                        Analista responsable
                      </label>
                      <input
                        id="reviewer"
                        type="text"
                        value={reviewer}
                        onChange={(e) => setReviewer(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 shadow-2xs focus:border-brand-500 focus:outline-hidden dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                        placeholder="analista@empresa.com"
                      />
                    </div>

                    <div>
                      <label htmlFor="comment" className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                        Justificación u Observaciones (opcional si aprueba, recomendado si rechaza)
                      </label>
                      <textarea
                        id="comment"
                        rows={3}
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-3 text-xs text-slate-900 shadow-2xs focus:border-brand-500 focus:outline-hidden dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                        placeholder="Ej: Se validó telefónicamente con el proveedor / Se solicita nota crédito por diferencia en precio..."
                      />
                    </div>

                    <div className="flex flex-col gap-3 pt-2 sm:flex-row sm:justify-end">
                      <button
                        type="button"
                        disabled={reviewMutation.isPending}
                        onClick={() => handleAction('RECHAZAR')}
                        className="inline-flex items-center justify-center gap-2 rounded-lg border border-rose-300 bg-white px-5 py-2.5 text-xs font-bold text-rose-700 shadow-xs hover:bg-rose-50 disabled:opacity-50 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300 dark:hover:bg-rose-900/60"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        Rechazar Factura
                      </button>

                      <button
                        type="button"
                        disabled={reviewMutation.isPending}
                        onClick={() => handleAction('APROBAR')}
                        className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-6 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-emerald-700 disabled:opacity-50"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                        </svg>
                        Aprobar Factura
                      </button>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
