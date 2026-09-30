import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import { fetchMetrics } from '../lib/api'
import type { DailyDecisionPoint, FindingMetricItem } from '../types/metrics'

function formatSeconds(ms: number): string {
  if (!ms || ms <= 0) return '0.0 s'
  return `${(ms / 1000).toFixed(1)} s`
}

function formatCost(cost: number | string | null | undefined): string {
  if (cost === null || cost === undefined) return '$0.0000 USD'
  const num = typeof cost === 'string' ? parseFloat(cost) : cost
  if (isNaN(num)) return '$0.0000 USD'
  return `$${num.toFixed(4)} USD`
}

function formatDateShort(dateStr: string): string {
  try {
    const parts = dateStr.split('-').map(Number)
    if (parts.length === 3) {
      const [year, month, day] = parts
      const d = new Date(year, month - 1, day)
      return d.toLocaleDateString('es-CO', { day: 'numeric', month: 'short' })
    }
    return dateStr
  } catch {
    return dateStr
  }
}

function SeverityBadge({ severity }: { severity: FindingMetricItem['severity'] }) {
  const styles: Record<FindingMetricItem['severity'], string> = {
    CRITICA: 'bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950/70 dark:text-rose-300 dark:border-rose-800',
    ALTA: 'bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-950/70 dark:text-orange-300 dark:border-orange-800',
    MEDIA: 'bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950/70 dark:text-amber-300 dark:border-amber-800',
    INFO: 'bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950/70 dark:text-blue-300 dark:border-blue-800',
  }

  return (
    <span className={`rounded border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider ${styles[severity] || styles.INFO}`}>
      {severity}
    </span>
  )
}

export function Dashboard() {
  const [hoveredDay, setHoveredDay] = useState<DailyDecisionPoint | null>(null)

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['system-metrics'],
    queryFn: fetchMetrics,
    refetchInterval: 30000, // Auto-refresh every 30 seconds
  })

  if (isLoading) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8 animate-pulse">
        <div className="h-10 w-72 rounded bg-slate-200 dark:bg-slate-800" />
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-5">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-32 rounded-xl bg-slate-200 dark:bg-slate-800" />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="h-80 rounded-xl bg-slate-200 dark:bg-slate-800 lg:col-span-2" />
          <div className="h-80 rounded-xl bg-slate-200 dark:bg-slate-800" />
        </div>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-center dark:border-rose-900/60 dark:bg-rose-950/30">
          <svg className="mx-auto h-12 w-12 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <h2 className="mt-3 text-lg font-semibold text-rose-900 dark:text-rose-200">Error al cargar métricas operativas</h2>
          <p className="mt-1 text-sm text-rose-700 dark:text-rose-400">
            {error instanceof Error ? error.message : 'No se pudo conectar con el servicio de métricas.'}
          </p>
          <button
            onClick={() => refetch()}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-700 shadow-sm"
          >
            Reintentar
          </button>
        </div>
      </div>
    )
  }

  const { kpis, decisions_summary, daily_decisions, top_findings } = data
  const totalDecisions = decisions_summary.total || 1
  const pctAprobar = Math.round((decisions_summary.aprobar / totalDecisions) * 100)
  const pctRevision = Math.round((decisions_summary.revision / totalDecisions) * 100)
  const pctRechazar = Math.round((decisions_summary.rechazar / totalDecisions) * 100)

  // Maximum daily total for chart bar scaling
  const maxDailyCount = Math.max(...daily_decisions.map((d) => d.total), 1)

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 sm:text-3xl">
              Dashboard de Operación AP
            </h1>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Pipeline Activo
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Monitoreo en tiempo real de procesamiento autónomo de facturas, Straight-Through Processing (STP) y detección de fraude.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800 transition disabled:opacity-50"
            title="Actualizar datos"
          >
            <svg
              className={`h-4 w-4 ${isFetching ? 'animate-spin text-brand-600' : 'text-slate-500 dark:text-slate-400'}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>{isFetching ? 'Actualizando...' : 'Actualizar'}</span>
          </button>

          <Link
            to="/upload"
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-brand-500 transition"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span>Procesar Factura</span>
          </Link>
        </div>
      </div>

      {/* 5 KPIs Operational Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {/* KPI 1: Facturas Procesadas */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Facturas Totales</span>
            <div className="rounded-lg bg-blue-50 p-2 text-blue-600 dark:bg-blue-950/60 dark:text-blue-400">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-slate-100">
              {kpis.total_invoices}
            </span>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              ({kpis.processed_invoices} completadas)
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">
            Ingestadas vía Azure Blob Storage
          </p>
        </div>

        {/* KPI 2: Aprobación Automática (STP) */}
        <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-5 shadow-xs dark:border-emerald-900/50 dark:bg-emerald-950/20">
          <div className="flex items-center justify-between text-emerald-700 dark:text-emerald-400">
            <span className="text-xs font-semibold uppercase tracking-wider">% Auto-Aprobación</span>
            <div className="rounded-lg bg-emerald-100 p-2 text-emerald-700 dark:bg-emerald-900/60 dark:text-emerald-300">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-emerald-700 dark:text-emerald-400">
              {kpis.auto_approval_rate_pct.toFixed(1)}%
            </span>
            <span className="text-xs font-semibold text-emerald-800 dark:text-emerald-300">
              STP
            </span>
          </div>
          <p className="mt-2 text-xs text-emerald-800/80 dark:text-emerald-300/80">
            {kpis.auto_approved_count} facturas sin intervención manual
          </p>
        </div>

        {/* KPI 3: Tiempo promedio de procesamiento */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Tiempo Promedio</span>
            <div className="rounded-lg bg-purple-50 p-2 text-purple-600 dark:bg-purple-950/60 dark:text-purple-400">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-slate-100">
              {formatSeconds(kpis.avg_processing_time_ms)}
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">
            vs. ~15-20 min por analista
          </p>
        </div>

        {/* KPI 4: Ahorro estimado de analista */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Ahorro Estimado</span>
            <div className="rounded-lg bg-amber-50 p-2 text-amber-600 dark:bg-amber-950/60 dark:text-amber-400">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-slate-100">
              {kpis.estimated_hours_saved.toFixed(1)} h
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">
            Horas hombre en cotejo y digitación
          </p>
        </div>

        {/* KPI 5: Costo IA Acumulado */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Costo IA Acumulado</span>
            <div className="rounded-lg bg-emerald-50 p-2 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-extrabold text-slate-900 dark:text-slate-100">
              {formatCost(kpis.total_ai_cost_usd)}
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">
            Azure Doc Intel + GPT-4o mini
          </p>
        </div>
      </div>

      {/* Main Grid: Decision Distribution & Daily Chart */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left 2 Cols: Gráfico de decisiones por día */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900 lg:col-span-2">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Actividad y Decisiones por Día
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Volumen diario procesado y distribución de decisiones
              </p>
            </div>

            {/* Chart Legend */}
            <div className="flex items-center gap-4 text-xs font-medium">
              <span className="inline-flex items-center gap-1.5 text-slate-700 dark:text-slate-300">
                <span className="h-3 w-3 rounded-xs bg-emerald-500" />
                Aprobadas
              </span>
              <span className="inline-flex items-center gap-1.5 text-slate-700 dark:text-slate-300">
                <span className="h-3 w-3 rounded-xs bg-amber-500" />
                Revisión
              </span>
              <span className="inline-flex items-center gap-1.5 text-slate-700 dark:text-slate-300">
                <span className="h-3 w-3 rounded-xs bg-rose-500" />
                Rechazadas
              </span>
            </div>
          </div>

          {/* Stacked Bar Chart */}
          <div className="mt-6">
            {daily_decisions.length === 0 ? (
              <div className="flex h-56 items-center justify-center rounded-lg border border-dashed border-slate-300 text-center text-sm text-slate-500 dark:border-slate-800 dark:text-slate-400">
                No hay actividad registrada en los últimos días
              </div>
            ) : (
              <div className="relative">
                {/* Chart Bars Container */}
                <div className="flex h-64 items-end gap-3 pt-8 pb-4">
                  {daily_decisions.map((day) => {
                    const heightPct = Math.max(12, Math.round((day.total / maxDailyCount) * 100))
                    const aprobarPct = day.total > 0 ? (day.aprobar / day.total) * 100 : 0
                    const revisionPct = day.total > 0 ? (day.revision / day.total) * 100 : 0
                    const rechazarPct = day.total > 0 ? (day.rechazar / day.total) * 100 : 0

                    const isHovered = hoveredDay?.date === day.date

                    return (
                      <div
                        key={day.date}
                        className="group relative flex flex-1 flex-col items-center h-full justify-end cursor-pointer"
                        onMouseEnter={() => setHoveredDay(day)}
                        onMouseLeave={() => setHoveredDay(null)}
                      >
                        {/* Day Total Number on Top */}
                        <span className="mb-1 text-[11px] font-bold text-slate-600 dark:text-slate-400">
                          {day.total}
                        </span>

                        {/* Stacked Vertical Bar */}
                        <div
                          style={{ height: `${heightPct}%` }}
                          className={`w-full max-w-[48px] rounded-t-md overflow-hidden flex flex-col-reverse transition-all duration-200 ${
                            isHovered ? 'ring-2 ring-brand-500 ring-offset-2 dark:ring-offset-slate-900 shadow-md scale-102' : 'hover:opacity-90'
                          }`}
                        >
                          {/* Segment: APROBAR (bottom) */}
                          {day.aprobar > 0 && (
                            <div
                              style={{ height: `${aprobarPct}%` }}
                              className="w-full bg-emerald-500 transition-all"
                              title={`Aprobadas: ${day.aprobar}`}
                            />
                          )}
                          {/* Segment: REVISIÓN (middle) */}
                          {day.revision > 0 && (
                            <div
                              style={{ height: `${revisionPct}%` }}
                              className="w-full bg-amber-500 transition-all"
                              title={`Revisión: ${day.revision}`}
                            />
                          )}
                          {/* Segment: RECHAZAR (top) */}
                          {day.rechazar > 0 && (
                            <div
                              style={{ height: `${rechazarPct}%` }}
                              className="w-full bg-rose-500 transition-all"
                              title={`Rechazadas: ${day.rechazar}`}
                            />
                          )}
                        </div>

                        {/* X-Axis Date Label */}
                        <span className="mt-2 text-[11px] font-medium text-slate-500 dark:text-slate-400 truncate max-w-full">
                          {formatDateShort(day.date)}
                        </span>
                      </div>
                    )
                  })}
                </div>

                {/* Hover Popover Tooltip */}
                {hoveredDay && (
                  <div className="mt-3 rounded-lg border border-slate-200 bg-slate-900 p-3 text-white shadow-xl dark:border-slate-700 dark:bg-slate-800 text-xs">
                    <div className="flex items-center justify-between border-b border-slate-700 pb-1.5 font-semibold">
                      <span>Fecha: {hoveredDay.date}</span>
                      <span className="text-slate-300">Total: {hoveredDay.total} facturas</span>
                    </div>
                    <div className="mt-2 grid grid-cols-3 gap-2">
                      <div className="flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-full bg-emerald-400" />
                        <span>Aprobadas: <strong>{hoveredDay.aprobar}</strong></span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-full bg-amber-400" />
                        <span>Revisión: <strong>{hoveredDay.revision}</strong></span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-full bg-rose-400" />
                        <span>Rechazadas: <strong>{hoveredDay.rechazar}</strong></span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right 1 Col: Desglose Acumulado de Decisiones */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900 flex flex-col justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Distribución de Decisiones
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Matriz determinista sobre {decisions_summary.total} facturas procesadas
            </p>

            {/* Proportion Bar */}
            <div className="mt-5 h-4 w-full overflow-hidden rounded-full bg-slate-100 flex dark:bg-slate-800">
              <div
                style={{ width: `${pctAprobar}%` }}
                className="bg-emerald-500 transition-all"
                title={`Aprobadas: ${pctAprobar}%`}
              />
              <div
                style={{ width: `${pctRevision}%` }}
                className="bg-amber-500 transition-all"
                title={`Revisión: ${pctRevision}%`}
              />
              <div
                style={{ width: `${pctRechazar}%` }}
                className="bg-rose-500 transition-all"
                title={`Rechazadas: ${pctRechazar}%`}
              />
            </div>

            {/* Breakdown Cards */}
            <div className="mt-6 space-y-3.5">
              {/* APROBAR */}
              <div className="flex items-center justify-between rounded-lg border border-emerald-100 bg-emerald-50/50 p-3 dark:border-emerald-950 dark:bg-emerald-950/20">
                <div className="flex items-center gap-2.5">
                  <div className="rounded-md bg-emerald-100 p-1.5 text-emerald-700 dark:bg-emerald-900/60 dark:text-emerald-300">
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-emerald-900 dark:text-emerald-200">APROBAR</span>
                    <p className="text-[11px] text-emerald-700 dark:text-emerald-400">3-Way match & DIAN OK</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-base font-extrabold text-emerald-800 dark:text-emerald-300">
                    {decisions_summary.aprobar}
                  </span>
                  <span className="block text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                    {pctAprobar}%
                  </span>
                </div>
              </div>

              {/* REVISIÓN */}
              <div className="flex items-center justify-between rounded-lg border border-amber-100 bg-amber-50/50 p-3 dark:border-amber-950 dark:bg-amber-950/20">
                <div className="flex items-center gap-2.5">
                  <div className="rounded-md bg-amber-100 p-1.5 text-amber-700 dark:bg-amber-900/60 dark:text-amber-300">
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-amber-900 dark:text-amber-200">REVISIÓN (HITL)</span>
                    <p className="text-[11px] text-amber-700 dark:text-amber-400">Discrepancias / Riesgo</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-base font-extrabold text-amber-800 dark:text-amber-300">
                    {decisions_summary.revision}
                  </span>
                  <span className="block text-[10px] font-medium text-amber-600 dark:text-amber-400">
                    {pctRevision}%
                  </span>
                </div>
              </div>

              {/* RECHAZAR */}
              <div className="flex items-center justify-between rounded-lg border border-rose-100 bg-rose-50/50 p-3 dark:border-rose-950 dark:bg-rose-950/20">
                <div className="flex items-center gap-2.5">
                  <div className="rounded-md bg-rose-100 p-1.5 text-rose-700 dark:bg-rose-900/60 dark:text-rose-300">
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-rose-900 dark:text-rose-200">RECHAZAR</span>
                    <p className="text-[11px] text-rose-700 dark:text-rose-400">Errores DIAN / Duplicados</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-base font-extrabold text-rose-800 dark:text-rose-300">
                    {decisions_summary.rechazar}
                  </span>
                  <span className="block text-[10px] font-medium text-rose-600 dark:text-rose-400">
                    {pctRechazar}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Quick link to Review queue if invoices in revision */}
          {decisions_summary.revision > 0 && (
            <Link
              to="/review"
              className="mt-6 flex items-center justify-between rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs font-semibold text-amber-900 hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200 transition"
            >
              <span>Hay {decisions_summary.revision} facturas en cola de revisión</span>
              <span className="flex items-center gap-1 text-amber-700 dark:text-amber-400">
                Revisar &rarr;
              </span>
            </Link>
          )}
        </div>
      </div>

      {/* Top Discrepancies & Fraud Findings */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Hallazgos y Discrepancias Frecuentes
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Causas de rechazo o derivación a revisión humana detectadas por las reglas deterministas de auditoría
            </p>
          </div>
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
            {top_findings.length} reglas activadas en el historial
          </span>
        </div>

        <div className="mt-6 overflow-hidden">
          {top_findings.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-800 dark:text-slate-400">
              No se han detectado inconsistencias ni alertas en las facturas procesadas.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-700 dark:text-slate-300">
                <thead className="border-b border-slate-200 text-xs font-semibold uppercase text-slate-500 dark:border-slate-800 dark:text-slate-400">
                  <tr>
                    <th scope="col" className="py-3 pr-4 pl-1">Código de Regla</th>
                    <th scope="col" className="px-4 py-3">Descripción de la Discrepancia</th>
                    <th scope="col" className="px-4 py-3 text-center">Severidad</th>
                    <th scope="col" className="px-4 py-3 text-right">Ocurrencias</th>
                    <th scope="col" className="py-3 pr-1 pl-4">Frecuencia</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-normal">
                  {top_findings.map((f, idx) => (
                    <tr key={f.code} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition">
                      <td className="py-3.5 pr-4 pl-1 font-mono text-xs font-semibold text-slate-900 dark:text-slate-100">
                        <span className="text-slate-400 mr-2">#{idx + 1}</span>
                        {f.code}
                      </td>
                      <td className="px-4 py-3.5 text-xs text-slate-800 dark:text-slate-200">
                        {f.label}
                      </td>
                      <td className="px-4 py-3.5 text-center">
                        <SeverityBadge severity={f.severity} />
                      </td>
                      <td className="px-4 py-3.5 text-right font-semibold text-slate-900 dark:text-slate-100">
                        {f.count}
                      </td>
                      <td className="py-3.5 pr-1 pl-4 min-w-[140px]">
                        <div className="flex items-center gap-2">
                          <div className="h-2 w-full max-w-[100px] overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                            <div
                              style={{ width: `${Math.min(100, Math.max(5, f.percentage))}%` }}
                              className={`h-full ${
                                f.severity === 'CRITICA'
                                  ? 'bg-rose-500'
                                  : f.severity === 'ALTA'
                                  ? 'bg-orange-500'
                                  : f.severity === 'MEDIA'
                                  ? 'bg-amber-500'
                                  : 'bg-blue-500'
                              }`}
                            />
                          </div>
                          <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                            {f.percentage}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* AP Business Value & Compliance Banner */}
      <div className="rounded-xl border border-slate-200 bg-gradient-to-r from-slate-900 to-slate-800 p-6 text-white shadow-md">
        <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-500/20 px-3 py-1 text-xs font-semibold text-brand-300">
              Auditoría AP y DIAN Colombia
            </span>
            <h3 className="mt-2 text-lg font-bold text-white">
              Cero Riesgo en Pagos y Cumplimiento Normativo
            </h3>
            <p className="mt-1 max-w-2xl text-xs text-slate-300 leading-relaxed">
              Validación criptográfica de CUFE (96 hex), algoritmo módulo 11 del Dígito de Verificación del NIT,
              3-way match estricto con tolerancia de precio (2%) y alerta preventiva inmediata ante suplantación
              o cambio de cuenta bancaria.
            </p>
          </div>

          <div className="flex shrink-0 flex-wrap items-center gap-3">
            <Link
              to="/invoices"
              className="rounded-lg bg-white px-4 py-2 text-xs font-bold text-slate-900 hover:bg-slate-100 transition shadow-xs"
            >
              Ver Bandeja de Facturas
            </Link>
            <Link
              to="/review"
              className="rounded-lg border border-slate-700 bg-slate-800/80 px-4 py-2 text-xs font-bold text-white hover:bg-slate-700 transition"
            >
              Cola de Revisión
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
