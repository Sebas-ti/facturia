import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import { fetchInvoices } from '../lib/api'
import type { DecisionType, FindingSeverity, InvoiceFilters, InvoiceListItem } from '../types/invoices'

function formatCop(amount: number | string): string {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount
  if (isNaN(num)) return '$ 0'
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  }).format(num)
}

function formatDate(dateStr: string | null): string {
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
      <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-300">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-500" />
        En proceso
      </span>
    )
  }

  if (status === 'ERROR') {
    return (
      <span className="inline-flex items-center rounded-full border border-slate-300 bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
        Error
      </span>
    )
  }

  switch (decision) {
    case 'APROBAR':
      return (
        <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300">
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
          </svg>
          APROBAR
        </span>
      )
    case 'REVISION':
      return (
        <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300">
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          REVISIÓN
        </span>
      )
    case 'RECHAZAR':
      return (
        <span className="inline-flex items-center gap-1 rounded-full border border-rose-200 bg-rose-50 px-2.5 py-0.5 text-xs font-semibold text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-300">
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
          </svg>
          RECHAZAR
        </span>
      )
    default:
      return (
        <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
          Pendiente
        </span>
      )
  }
}

function FindingChip({ code, severity, message }: { code: string; severity: FindingSeverity; message: string }) {
  const colorMap: Record<FindingSeverity, string> = {
    CRITICA:
      'bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950/70 dark:text-rose-300 dark:border-rose-800 font-semibold',
    ALTA:
      'bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-950/70 dark:text-orange-300 dark:border-orange-800',
    MEDIA:
      'bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950/70 dark:text-amber-300 dark:border-amber-800',
    INFO:
      'bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700',
  }

  return (
    <span
      title={`${code}: ${message}`}
      className={`inline-flex max-w-[200px] truncate items-center rounded border px-2 py-0.5 text-[11px] transition ${colorMap[severity] || colorMap.INFO}`}
    >
      {code}
    </span>
  )
}

export function Invoices() {
  const [searchInput, setSearchInput] = useState('')
  const [filters, setFilters] = useState<InvoiceFilters>({
    page: 1,
    page_size: 10,
  })

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['invoices', filters],
    queryFn: () => fetchInvoices(filters),
  })

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setFilters((prev) => ({
      ...prev,
      search: searchInput.trim() || undefined,
      page: 1,
    }))
  }

  const handleDecisionChange = (decision: string) => {
    setFilters((prev) => ({
      ...prev,
      decision: decision || undefined,
      page: 1,
    }))
  }

  const handleStatusChange = (status: string) => {
    setFilters((prev) => ({
      ...prev,
      status: status || undefined,
      page: 1,
    }))
  }

  const handleToggleBankAlert = () => {
    setFilters((prev) => ({
      ...prev,
      bank_account_alert: prev.bank_account_alert ? undefined : true,
      page: 1,
    }))
  }

  const handleResetFilters = () => {
    setSearchInput('')
    setFilters({
      page: 1,
      page_size: 10,
    })
  }

  const hasActiveFilters = Boolean(
    filters.search || filters.decision || filters.status || filters.bank_account_alert !== undefined
  )

  // Check if any invoice on current page has bank account alert
  const hasBankAlertInResults = data?.items.some((inv) => inv.has_bank_account_alert)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 sm:text-3xl">
            Bandeja de Facturas
          </h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Monitorea el procesamiento multiagente, revisa hallazgos y autoriza pagos.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-xs hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <svg
              className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Actualizar
          </button>
          <Link
            to="/upload"
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-xs hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Subir factura
          </Link>
        </div>
      </div>

      {/* Critical Fraud Alert Callout */}
      {(hasBankAlertInResults || filters.bank_account_alert) && (
        <div className="flex flex-col gap-3 rounded-xl border border-rose-300 bg-rose-50/90 p-4 shadow-xs sm:flex-row sm:items-center sm:justify-between dark:border-rose-900/70 dark:bg-rose-950/30">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-100 text-rose-600 dark:bg-rose-900/50 dark:text-rose-400">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <div>
              <h2 className="text-sm font-semibold text-rose-900 dark:text-rose-200">
                Alerta Crítica: Cambio de Cuenta Bancaria Detectado
              </h2>
              <p className="mt-0.5 text-xs text-rose-700 dark:text-rose-300">
                Se detectaron facturas donde la cuenta bancaria impresa no coincide con la registrada en el maestro de proveedores. Requieren verificación urgente para mitigar riesgos de suplantación.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleToggleBankAlert}
            className={`shrink-0 rounded-lg px-3 py-1.5 text-xs font-semibold shadow-xs transition ${
              filters.bank_account_alert
                ? 'bg-rose-700 text-white hover:bg-rose-800 dark:bg-rose-600 dark:hover:bg-rose-500'
                : 'border border-rose-300 bg-white text-rose-800 hover:bg-rose-100 dark:border-rose-800 dark:bg-rose-900/40 dark:text-rose-200'
            }`}
          >
            {filters.bank_account_alert ? 'Mostrar todas' : 'Ver solo alertas de cuenta'}
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900/50">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4">
          {/* Search Box */}
          <form onSubmit={handleSearchSubmit} className="relative col-span-1 sm:col-span-2">
            <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </span>
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Buscar por número, proveedor o NIT..."
              className="w-full rounded-lg border border-slate-300 bg-slate-50/50 py-2 pr-20 pl-9 text-sm text-slate-900 placeholder-slate-400 focus:border-brand-500 focus:bg-white focus:outline-hidden focus:ring-1 focus:ring-brand-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:border-brand-400 dark:focus:bg-slate-900"
            />
            <button
              type="submit"
              className="absolute inset-y-1 right-1 rounded-md bg-slate-200 px-2.5 text-xs font-medium text-slate-700 hover:bg-slate-300 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
            >
              Buscar
            </button>
          </form>

          {/* Decision Filter */}
          <div>
            <select
              value={filters.decision ?? ''}
              onChange={(e) => handleDecisionChange(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-slate-50/50 px-3 py-2 text-sm text-slate-900 focus:border-brand-500 focus:bg-white focus:outline-hidden focus:ring-1 focus:ring-brand-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            >
              <option value="">Todas las decisiones</option>
              <option value="APROBAR">Aprobar</option>
              <option value="REVISION">Revisión</option>
              <option value="RECHAZAR">Rechazar</option>
            </select>
          </div>

          {/* Status Filter */}
          <div>
            <select
              value={filters.status ?? ''}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-slate-50/50 px-3 py-2 text-sm text-slate-900 focus:border-brand-500 focus:bg-white focus:outline-hidden focus:ring-1 focus:ring-brand-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            >
              <option value="">Todos los estados</option>
              <option value="PROCESSED">Procesada</option>
              <option value="PROCESSING">En proceso</option>
              <option value="ERROR">Con error</option>
            </select>
          </div>
        </div>

        {/* Active filters and Clear button */}
        {hasActiveFilters && (
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3 text-xs dark:border-slate-800">
            <div className="flex flex-wrap items-center gap-2 text-slate-600 dark:text-slate-400">
              <span className="font-medium">Filtros activos:</span>
              {filters.search && (
                <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 dark:bg-slate-800">
                  Texto: &ldquo;{filters.search}&rdquo;
                </span>
              )}
              {filters.decision && (
                <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 dark:bg-slate-800">
                  Decisión: {filters.decision}
                </span>
              )}
              {filters.status && (
                <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 dark:bg-slate-800">
                  Estado: {filters.status}
                </span>
              )}
              {filters.bank_account_alert && (
                <span className="inline-flex items-center gap-1 rounded bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300 px-2 py-0.5">
                  Solo cambio de cuenta
                </span>
              )}
            </div>
            <button
              type="button"
              onClick={handleResetFilters}
              className="font-medium text-brand-600 hover:text-brand-700 hover:underline dark:text-brand-400"
            >
              Limpiar filtros
            </button>
          </div>
        )}
      </div>

      {/* Table & States */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs dark:border-slate-800 dark:bg-slate-900/50">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="inline-flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
              Cargando facturas...
            </div>
          </div>
        ) : isError ? (
          <div className="p-8 text-center">
            <p className="text-sm font-medium text-rose-600 dark:text-rose-400">
              {error instanceof Error ? error.message : 'Error al cargar las facturas'}
            </p>
            <button
              type="button"
              onClick={() => refetch()}
              className="mt-3 inline-flex items-center gap-1 rounded-md bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"
            >
              Reintentar
            </button>
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="px-6 py-16 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="mt-3 text-sm font-semibold text-slate-900 dark:text-slate-100">
              No hay facturas para mostrar
            </h3>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              {hasActiveFilters
                ? 'Prueba ajustando los filtros de búsqueda.'
                : 'Aún no se han procesado facturas en el sistema.'}
            </p>
            <div className="mt-5 flex items-center justify-center gap-3">
              {hasActiveFilters ? (
                <button
                  type="button"
                  onClick={handleResetFilters}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  Restablecer filtros
                </button>
              ) : (
                <Link
                  to="/upload"
                  className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 dark:bg-brand-500"
                >
                  Subir la primera factura
                </Link>
              )}
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/75 text-xs font-semibold tracking-wider text-slate-600 uppercase dark:border-slate-800 dark:bg-slate-900/80 dark:text-slate-400">
                <tr>
                  <th className="py-3.5 pr-3 pl-4 sm:pl-6">Factura</th>
                  <th className="px-3 py-3.5">Proveedor</th>
                  <th className="px-3 py-3.5">Fecha</th>
                  <th className="px-3 py-3.5 text-right">Total (COP)</th>
                  <th className="px-3 py-3.5 text-center">Decisión</th>
                  <th className="px-3 py-3.5">Hallazgos</th>
                  <th className="py-3.5 pr-4 pl-3 text-right sm:pr-6">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {data.items.map((invoice: InvoiceListItem) => (
                  <tr
                    key={invoice.id}
                    className={`transition hover:bg-slate-50/70 dark:hover:bg-slate-800/40 ${
                      invoice.has_bank_account_alert
                        ? 'border-l-4 border-l-rose-500 bg-rose-50/30 dark:bg-rose-950/20'
                        : ''
                    }`}
                  >
                    {/* Invoice number + hash badge */}
                    <td className="py-3.5 pr-3 pl-4 sm:pl-6">
                      <div className="flex flex-col">
                        <Link
                          to={`/invoices/${invoice.id}`}
                          className="font-medium text-brand-600 hover:text-brand-700 hover:underline dark:text-brand-400 dark:hover:text-brand-300"
                        >
                          {invoice.invoice_number || 'PENDIENTE'}
                        </Link>
                        {invoice.has_bank_account_alert && (
                          <span className="mt-0.5 inline-flex items-center gap-1 text-[11px] font-semibold text-rose-600 dark:text-rose-400">
                            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01" />
                            </svg>
                            Alerta de fraude
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Supplier */}
                    <td className="px-3 py-3.5">
                      <div className="flex flex-col">
                        <span className="font-medium text-slate-900 dark:text-slate-100">
                          {invoice.supplier_name || 'Desconocido'}
                        </span>
                        {invoice.supplier_nit && (
                          <span className="text-xs text-slate-500 dark:text-slate-400">
                            NIT: {invoice.supplier_nit}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Date */}
                    <td className="px-3 py-3.5 text-xs text-slate-600 whitespace-nowrap dark:text-slate-400">
                      {formatDate(invoice.issue_date)}
                    </td>

                    {/* Total */}
                    <td className="px-3 py-3.5 text-right font-medium text-slate-900 whitespace-nowrap dark:text-slate-100">
                      {formatCop(invoice.total)}
                    </td>

                    {/* Decision */}
                    <td className="px-3 py-3.5 text-center whitespace-nowrap">
                      <DecisionBadge decision={invoice.decision} status={invoice.status} />
                    </td>

                    {/* Findings chips */}
                    <td className="px-3 py-3.5">
                      {invoice.findings.length > 0 ? (
                        <div className="flex max-w-xs flex-wrap gap-1">
                          {invoice.findings.slice(0, 3).map((f) => (
                            <FindingChip
                              key={f.id}
                              code={f.code}
                              severity={f.severity}
                              message={f.message}
                            />
                          ))}
                          {invoice.findings.length > 3 && (
                            <span className="inline-flex items-center rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                              +{invoice.findings.length - 3}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400 dark:text-slate-500">—</span>
                      )}
                    </td>

                    {/* Action */}
                    <td className="py-3.5 pr-4 pl-3 text-right whitespace-nowrap sm:pr-6">
                      <Link
                        to={`/invoices/${invoice.id}`}
                        className="inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                      >
                        Ver detalle
                        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        {data && data.total > 0 && (
          <div className="flex flex-col items-center justify-between gap-3 border-t border-slate-200 bg-slate-50/50 px-4 py-3 sm:flex-row sm:px-6 dark:border-slate-800 dark:bg-slate-900/60">
            <div className="text-xs text-slate-500 dark:text-slate-400">
              Mostrando{' '}
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {(data.page - 1) * data.page_size + 1}
              </span>{' '}
              a{' '}
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {Math.min(data.page * data.page_size, data.total)}
              </span>{' '}
              de{' '}
              <span className="font-semibold text-slate-800 dark:text-slate-200">{data.total}</span>{' '}
              facturas
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setFilters((prev) => ({ ...prev, page: Math.max(1, (prev.page || 1) - 1) }))}
                disabled={data.page <= 1 || isLoading}
                className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 shadow-xs hover:bg-slate-50 disabled:opacity-40 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              >
                Anterior
              </button>
              <span className="px-2 text-xs font-medium text-slate-600 dark:text-slate-400">
                {data.page} / {data.total_pages}
              </span>
              <button
                type="button"
                onClick={() => setFilters((prev) => ({ ...prev, page: Math.min(data.total_pages, (prev.page || 1) + 1) }))}
                disabled={data.page >= data.total_pages || isLoading}
                className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 shadow-xs hover:bg-slate-50 disabled:opacity-40 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
