import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import { fetchEvalReports } from '../lib/api'
import type { ConfusionMatrixRow, FieldAccuracyItem, FindingAccuracyItem, InvoiceCaseResult } from '../types/evals'

const FIELD_LABELS: Record<string, string> = {
  supplier_nit: 'NIT del Proveedor',
  supplier_dv: 'Dígito de Verificación (DV)',
  supplier_name: 'Razón Social Proveedor',
  invoice_number: 'Número de Factura',
  issue_date: 'Fecha de Emisión',
  due_date: 'Fecha de Vencimiento',
  purchase_order: 'Número de Orden de Compra',
  subtotal: 'Subtotal sin Impuestos',
  vat_total: 'Total IVA',
  total: 'Total Factura',
  cufe: 'Código Único CUFE (96 hex)',
  bank_account: 'Datos de Cuenta Bancaria',
  sku: 'Código SKU Línea',
  description: 'Descripción de Producto',
  quantity: 'Cantidad Facturada',
  unit_price: 'Precio Unitario',
  vat_rate: 'Tarifa IVA Línea (%)',
  line_subtotal: 'Subtotal de Línea',
}

const FINDING_LABELS: Record<string, string> = {
  INVALID_NIT_DV: 'Dígito de Verificación Erróneo (DIAN)',
  ARITHMETIC_ERROR: 'Error Aritmético en Totales / Líneas',
  INVALID_CUFE: 'Formato CUFE Inválido (96 hex)',
  INCOHERENT_DATES: 'Fechas Incoherentes (Vencimiento < Emisión)',
  UNKNOWN_SUPPLIER: 'Proveedor No Registrado en Maestro',
  MISSING_PO: 'Sin Orden de Compra de Referencia',
  PRICE_MISMATCH: 'Discrepancia de Precio vs OC (>2%)',
  QTY_EXCEEDS_RECEIPT: 'Cantidad Facturada Excede Recepción',
  DUPLICATE_INVOICE: 'Factura Duplicada en Base de Datos',
  BANK_ACCOUNT_CHANGED: 'Alerta Crítica: Cambio de Cuenta Bancaria',
  LOW_CONFIDENCE_EXTRACTION: 'Baja Confianza en OCR Document Intelligence',
  AMOUNT_OVER_THRESHOLD: 'Monto Excede Umbral de Aprobación',
}

export function Evals() {
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'decision' | 'fields' | 'findings' | 'raw'>('decision')
  const [copiedRaw, setCopiedRaw] = useState(false)

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['eval-reports', selectedReportId],
    queryFn: () => fetchEvalReports(selectedReportId ?? undefined),
  })

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedRaw(true)
      setTimeout(() => setCopiedRaw(false), 2000)
    } catch {
      // Fallback
    }
  }

  if (isLoading) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8 animate-pulse">
        <div className="h-10 w-80 rounded bg-slate-200 dark:bg-slate-800" />
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 rounded-xl bg-slate-200 dark:bg-slate-800" />
          ))}
        </div>
        <div className="h-96 rounded-xl bg-slate-200 dark:bg-slate-800" />
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
          <h2 className="mt-3 text-lg font-semibold text-rose-900 dark:text-rose-200">Error al cargar reportes de evaluación</h2>
          <p className="mt-1 text-sm text-rose-700 dark:text-rose-400">
            {error instanceof Error ? error.message : 'No se pudo conectar con el servicio de evals.'}
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

  const { reports, selected } = data
  const { confusion_matrix, extraction_accuracy, findings_accuracy, invoice_cases } = selected

  // Compute average extraction precision across all tested fields
  const avgExtractionPrecision =
    extraction_accuracy.length > 0
      ? (
          extraction_accuracy.reduce((acc, item) => acc + item.precision_pct, 0) /
          extraction_accuracy.length
        ).toFixed(1)
      : '0.0'

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      {/* Header Section */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 sm:text-3xl">
              Evaluación Continua (Evals)
            </h1>
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider ${
                selected.mode === 'live'
                  ? 'border border-purple-200 bg-purple-50 text-purple-800 dark:border-purple-900/60 dark:bg-purple-950/40 dark:text-purple-300'
                  : 'border border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-300'
              }`}
            >
              Modo {selected.mode === 'live' ? 'Azure Real (Live)' : 'Mock (Ground Truth)'}
            </span>
            {selected.overall_accuracy_pct === 100 && (
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300">
                100% Precisión
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400 max-w-3xl">
            Verificación automatizada del pipeline LangGraph contra el dataset de ground truth (15 facturas diseñadas para validar
            OCR, reglas tributarias DIAN, matching 3-way y detección de fraude).
          </p>
        </div>

        {/* Report Selector & Actions */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <label htmlFor="report-select" className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              Reporte:
            </label>
            <select
              id="report-select"
              value={selected.id}
              onChange={(e) => setSelectedReportId(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-800 focus:border-brand-500 focus:outline-hidden dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
            >
              {reports.map((rep) => (
                <option key={rep.id} value={rep.id}>
                  {rep.filename} ({rep.mode.toUpperCase()}) — {rep.accuracy_pct}%
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800 transition disabled:opacity-50"
            title="Recargar reporte"
          >
            <svg
              className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin text-brand-600' : 'text-slate-500'}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>{isFetching ? 'Cargando...' : 'Recargar'}</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Summary */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Decision Accuracy */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Exactitud de Decisión</span>
            <div className="rounded-lg bg-emerald-50 p-2 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-slate-100">
              {selected.overall_accuracy_pct}%
            </span>
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
              ({selected.successful_cases}/{selected.total_cases} facturas)
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">
            Aprobación, revisión y rechazo deterministas
          </p>
        </div>

        {/* Extraction Accuracy */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Precisión Extracción</span>
            <div className="rounded-lg bg-blue-50 p-2 text-blue-600 dark:bg-blue-950/60 dark:text-blue-400">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-slate-100">
              {avgExtractionPrecision}%
            </span>
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
              promedio ({extraction_accuracy.length} campos)
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">
            Encabezados, impuestos y detalle de líneas
          </p>
        </div>

        {/* Audit Rules Evaluated */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Reglas Auditadas</span>
            <div className="rounded-lg bg-amber-50 p-2 text-amber-600 dark:bg-amber-950/60 dark:text-amber-400">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-slate-100">
              {findings_accuracy.length}
            </span>
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
              códigos de hallazgo
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">
            NIT, CUFE, aritmética, matching y fraude
          </p>
        </div>

        {/* Execution Metadata */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Archivo de Reporte</span>
            <div className="rounded-lg bg-purple-50 p-2 text-purple-600 dark:bg-purple-950/60 dark:text-purple-400">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
              </svg>
            </div>
          </div>
          <div className="mt-3 font-mono text-xs font-bold text-slate-900 dark:text-slate-100 truncate">
            {selected.filename}
          </div>
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400 truncate">
            Generado: {selected.generated_at || 'Reciente'}
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-slate-200 dark:border-slate-800">
        <nav className="-mb-px flex space-x-6">
          <button
            onClick={() => setActiveTab('decision')}
            className={`cursor-pointer pb-3 text-sm font-semibold transition border-b-2 ${
              activeTab === 'decision'
                ? 'border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400'
                : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            Matriz de Confusión y Casos ({invoice_cases.length})
          </button>
          <button
            onClick={() => setActiveTab('fields')}
            className={`cursor-pointer pb-3 text-sm font-semibold transition border-b-2 ${
              activeTab === 'fields'
                ? 'border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400'
                : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            Extracción por Campo ({extraction_accuracy.length})
          </button>
          <button
            onClick={() => setActiveTab('findings')}
            className={`cursor-pointer pb-3 text-sm font-semibold transition border-b-2 ${
              activeTab === 'findings'
                ? 'border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400'
                : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            Hallazgos y Reglas ({findings_accuracy.length})
          </button>
          <button
            onClick={() => setActiveTab('raw')}
            className={`cursor-pointer pb-3 text-sm font-semibold transition border-b-2 ${
              activeTab === 'raw'
                ? 'border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400'
                : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            Reporte Markdown Original
          </button>
        </nav>
      </div>

      {/* Tab 1: Confusion Matrix & Cases */}
      {activeTab === 'decision' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Confusion Matrix Table */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                    Matriz de Confusión de Decisiones
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Comparación de Decisión Esperada (Filas) vs. Decisión Obtenida (Columnas)
                  </p>
                </div>
                <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-bold text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-300">
                  {confusion_matrix.accuracy_pct}% Accuracy
                </span>
              </div>

              <div className="mt-6 overflow-x-auto">
                <table className="w-full text-center text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-800">
                      <th className="py-2.5 px-3 text-left font-semibold text-slate-500 dark:text-slate-400">
                        Esperada \ Obtenida
                      </th>
                      <th className="py-2.5 px-3 font-semibold text-emerald-700 dark:text-emerald-400">
                        APROBAR
                      </th>
                      <th className="py-2.5 px-3 font-semibold text-amber-700 dark:text-amber-400">
                        REVISIÓN
                      </th>
                      <th className="py-2.5 px-3 font-semibold text-rose-700 dark:text-rose-400">
                        RECHAZAR
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-medium">
                    {confusion_matrix.rows.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="py-8 text-center text-slate-400">
                          Sin matriz de confusión en este reporte.
                        </td>
                      </tr>
                    ) : (
                      confusion_matrix.rows.map((row: ConfusionMatrixRow) => (
                        <tr key={row.expected}>
                          <td className="py-3 px-3 text-left font-bold text-slate-700 dark:text-slate-300">
                            {row.expected}
                          </td>
                          {/* APROBAR cell */}
                          <td className="py-3 px-3">
                            <span
                              className={`inline-flex items-center justify-center h-8 w-12 rounded-lg font-bold text-xs ${
                                row.expected === 'APROBAR' && row.aprobar > 0
                                  ? 'bg-emerald-500 text-white shadow-xs'
                                  : row.aprobar > 0
                                  ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 font-bold'
                                  : 'text-slate-400 dark:text-slate-600'
                              }`}
                            >
                              {row.aprobar}
                            </span>
                          </td>
                          {/* REVISION cell */}
                          <td className="py-3 px-3">
                            <span
                              className={`inline-flex items-center justify-center h-8 w-12 rounded-lg font-bold text-xs ${
                                row.expected === 'REVISION' && row.revision > 0
                                  ? 'bg-emerald-500 text-white shadow-xs'
                                  : row.revision > 0
                                  ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 font-bold'
                                  : 'text-slate-400 dark:text-slate-600'
                              }`}
                            >
                              {row.revision}
                            </span>
                          </td>
                          {/* RECHAZAR cell */}
                          <td className="py-3 px-3">
                            <span
                              className={`inline-flex items-center justify-center h-8 w-12 rounded-lg font-bold text-xs ${
                                row.expected === 'RECHAZAR' && row.rechazar > 0
                                  ? 'bg-emerald-500 text-white shadow-xs'
                                  : row.rechazar > 0
                                  ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 font-bold'
                                  : 'text-slate-400 dark:text-slate-600'
                              }`}
                            >
                              {row.rechazar}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              <div className="mt-4 flex items-center justify-between text-[11px] text-slate-500 border-t border-slate-100 pt-3 dark:border-slate-800">
                <span>Casos clasificados correctamente: <strong>{confusion_matrix.correct}</strong></span>
                <span>Total de evaluaciones: <strong>{confusion_matrix.total}</strong></span>
              </div>
            </div>

            {/* Decision Logic & Spec Rules Info */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900 flex flex-col justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  Matriz de Decisión Determinista (Spec §4.2)
                </h2>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  El sistema no delega la decisión a la aleatoriedad de un LLM: aplica una máquina de estados pura.
                </p>

                <div className="mt-4 space-y-2.5 text-xs text-slate-700 dark:text-slate-300">
                  <div className="rounded-lg border border-rose-200 bg-rose-50/60 p-2.5 dark:border-rose-900/60 dark:bg-rose-950/20">
                    <span className="font-bold text-rose-800 dark:text-rose-300">RECHAZAR Inmediato:</span>
                    <p className="text-[11px] text-rose-700 dark:text-rose-400 mt-0.5">
                      DV del NIT erróneo, error aritmético en totales o factura duplicada preexistente en la base de datos.
                    </p>
                  </div>
                  <div className="rounded-lg border border-amber-200 bg-amber-50/60 p-2.5 dark:border-amber-900/60 dark:bg-amber-950/20">
                    <span className="font-bold text-amber-800 dark:text-amber-300">REVISIÓN Humana (HITL):</span>
                    <p className="text-[11px] text-amber-700 dark:text-amber-400 mt-0.5">
                      Cambio no autorizado de cuenta bancaria, proveedor nuevo no registrado, discrepancia de precio (&gt;2%), cantidad excedida o monto superior a $20M COP.
                    </p>
                  </div>
                  <div className="rounded-lg border border-emerald-200 bg-emerald-50/60 p-2.5 dark:border-emerald-900/60 dark:bg-emerald-950/20">
                    <span className="font-bold text-emerald-800 dark:text-emerald-300">APROBAR Automático:</span>
                    <p className="text-[11px] text-emerald-700 dark:text-emerald-400 mt-0.5">
                      3-way match perfecto contra órdenes de compra y recepciones, algoritmos DIAN conformes y sin alertas de fraude.
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-4 border-t border-slate-100 pt-3 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400">
                Garantía: Todo rechazo genera borrador de correo formal para el proveedor redactado por Azure OpenAI.
              </div>
            </div>
          </div>

          {/* Individual Invoice Cases Table */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  Resultado Factura por Factura ({invoice_cases.length} Casos)
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Desglose de ejecución sobre el dataset sintético oficial de FacturIA
                </p>
              </div>
              <span className="text-xs font-semibold text-slate-500">
                {invoice_cases.filter((c) => c.status === 'OK').length}/{invoice_cases.length} aprobadas sin discrepancia
              </span>
            </div>

            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-200 dark:border-slate-800 text-slate-500 font-semibold uppercase">
                  <tr>
                    <th scope="col" className="py-2.5 px-3">Factura</th>
                    <th scope="col" className="py-2.5 px-3">Estado</th>
                    <th scope="col" className="py-2.5 px-3">Detalle / Diferencias Encontradas</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-medium">
                  {invoice_cases.map((c: InvoiceCaseResult) => (
                    <tr key={c.invoice_id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition">
                      <td className="py-3 px-3 font-mono font-bold text-slate-900 dark:text-slate-100">
                        {c.invoice_id}
                      </td>
                      <td className="py-3 px-3">
                        {c.status === 'OK' ? (
                          <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-bold text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300">
                            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                            </svg>
                            OK
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full border border-rose-200 bg-rose-50 px-2 py-0.5 text-[11px] font-bold text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-300">
                            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                            FALLA
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-slate-600 dark:text-slate-400 font-mono text-[11px]">
                        {c.detail ? (
                          <span className="text-rose-700 dark:text-rose-400">{c.detail}</span>
                        ) : (
                          <span className="text-slate-400">— Sin discrepancias con ground truth —</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Extraction Accuracy */}
      {activeTab === 'fields' && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Precisión de Extracción por Campo ({extraction_accuracy.length} Campos)
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Evaluación campo a campo comparando Document Intelligence + normalizador contra el ground truth
              </p>
            </div>
            <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">
              Promedio General: {avgExtractionPrecision}%
            </span>
          </div>

          <div className="mt-6 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 dark:border-slate-800 text-slate-500 font-semibold uppercase">
                <tr>
                  <th scope="col" className="py-3 px-3">Identificador</th>
                  <th scope="col" className="py-3 px-3">Descripción del Campo</th>
                  <th scope="col" className="py-3 px-3 text-center">Precisión</th>
                  <th scope="col" className="py-3 px-3 text-center">Aciertos / Total</th>
                  <th scope="col" className="py-3 px-3 min-w-[160px]">Rendimiento</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-medium">
                {extraction_accuracy.map((f: FieldAccuracyItem) => (
                  <tr key={f.field} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition">
                    <td className="py-3 px-3 font-mono font-bold text-slate-900 dark:text-slate-100">
                      `{f.field}`
                    </td>
                    <td className="py-3 px-3 text-slate-700 dark:text-slate-300">
                      {FIELD_LABELS[f.field] || f.field}
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span
                        className={`inline-block font-bold ${
                          f.precision_pct >= 95
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : f.precision_pct >= 80
                            ? 'text-amber-600 dark:text-amber-400'
                            : 'text-rose-600 dark:text-rose-400'
                        }`}
                      >
                        {f.precision_pct}%
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center text-slate-600 dark:text-slate-400">
                      {f.hits} / {f.total}
                    </td>
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-full max-w-[120px] overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                          <div
                            style={{ width: `${Math.max(4, f.precision_pct)}%` }}
                            className={`h-full ${
                              f.precision_pct >= 95
                                ? 'bg-emerald-500'
                                : f.precision_pct >= 80
                                ? 'bg-amber-500'
                                : 'bg-rose-500'
                            }`}
                          />
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Findings Precision & Recall */}
      {activeTab === 'findings' && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Precisión y Recall en Detección de Discrepancias ({findings_accuracy.length} Códigos)
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Métricas de clasificación para reglas de matching, DIAN, validación aritmética y fraude
              </p>
            </div>
            <span className="text-xs font-semibold text-slate-500">
              TP = Verdaderos Positivos · FP = Falsos Positivos · FN = Falsos Negativos
            </span>
          </div>

          <div className="mt-6 overflow-x-auto">
            {findings_accuracy.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400">
                Sin métricas de hallazgos en este reporte (corrida de extracción temprana).
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-200 dark:border-slate-800 text-slate-500 font-semibold uppercase">
                  <tr>
                    <th scope="col" className="py-3 px-3">Código de Regla</th>
                    <th scope="col" className="py-3 px-3">Descripción</th>
                    <th scope="col" className="py-3 px-3 text-center">Precisión</th>
                    <th scope="col" className="py-3 px-3 text-center">Recall</th>
                    <th scope="col" className="py-3 px-3 text-center">TP</th>
                    <th scope="col" className="py-3 px-3 text-center">FP</th>
                    <th scope="col" className="py-3 px-3 text-center">FN</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-medium">
                  {findings_accuracy.map((f: FindingAccuracyItem) => (
                    <tr key={f.code} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition">
                      <td className="py-3 px-3 font-mono font-bold text-slate-900 dark:text-slate-100">
                        {f.code}
                      </td>
                      <td className="py-3 px-3 text-slate-700 dark:text-slate-300">
                        {FINDING_LABELS[f.code] || f.code}
                      </td>
                      <td className="py-3 px-3 text-center font-bold text-emerald-600 dark:text-emerald-400">
                        {f.precision_pct}%
                      </td>
                      <td className="py-3 px-3 text-center font-bold text-blue-600 dark:text-blue-400">
                        {f.recall_pct}%
                      </td>
                      <td className="py-3 px-3 text-center font-semibold text-slate-800 dark:text-slate-200">
                        {f.tp}
                      </td>
                      <td className="py-3 px-3 text-center font-semibold text-rose-600 dark:text-rose-400">
                        {f.fp}
                      </td>
                      <td className="py-3 px-3 text-center font-semibold text-amber-600 dark:text-amber-400">
                        {f.fn}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* Tab 4: Raw Markdown */}
      {activeTab === 'raw' && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Archivo Markdown del Benchmark
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Salida íntegra generada por el runner de evaluación de CI/CD
              </p>
            </div>
            <button
              onClick={() => copyToClipboard(selected.raw_markdown)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700 transition"
            >
              {copiedRaw ? (
                <>
                  <svg className="h-4 w-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span>Copiado</span>
                </>
              ) : (
                <>
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  <span>Copiar Markdown</span>
                </>
              )}
            </button>
          </div>

          <pre className="mt-4 max-h-[500px] overflow-auto rounded-lg bg-slate-900 p-4 font-mono text-xs text-slate-100 dark:bg-slate-950">
            {selected.raw_markdown}
          </pre>
        </div>
      )}

      {/* CI/CD & Portfolio Banner */}
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 dark:border-slate-800 dark:bg-slate-900/60">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              Evaluación Automática en CI/CD con GitHub Actions
            </h3>
            <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
              Cada Pull Request y push a la rama principal ejecuta <code className="rounded bg-slate-200 px-1 py-0.5 text-slate-800 dark:bg-slate-800 dark:text-slate-200">evals/run_evals.py --mock</code> garantizando que ninguna modificación de código introduzca regresiones en la matriz de decisión o en las reglas tributarias de la DIAN.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-1 text-xs font-semibold text-brand-600 hover:text-brand-500 dark:text-brand-400"
            >
              Ver métricas en vivo &rarr;
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
