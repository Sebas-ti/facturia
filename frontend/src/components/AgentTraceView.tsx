import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { AgentRunItem, DecisionType, InvoiceTraceResponse } from '../types/invoices'

interface AgentTraceViewProps {
  trace: InvoiceTraceResponse | null | undefined
  isLoading: boolean
  invoiceId: string
  decision: DecisionType | null
}

interface NodeInfo {
  title: string
  subtitle: string
  technology: string
  tagStyle: string
  description: string
}

const NODE_INFO: Record<string, NodeInfo> = {
  ingest: {
    title: 'Ingesta y Verificación de Documento',
    subtitle: 'Extracción de hash SHA-256 y detección de escaneo',
    technology: 'PyPDF + Azure Blob Storage',
    tagStyle: 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-300',
    description:
      'Calcula el hash criptográfico SHA-256 para evitar duplicidad a nivel de archivo, determina si el PDF es escaneado por densidad de caracteres y almacena el binario en Azure Blob Storage (Azurite en local).',
  },
  extract: {
    title: 'Extracción Estructurada con IA',
    subtitle: 'Modelo de factura preentrenado + resolución LLM',
    technology: 'Azure Doc Intelligence + Azure OpenAI',
    tagStyle: 'border-purple-200 bg-purple-50 text-purple-700 dark:border-purple-900/60 dark:bg-purple-950/40 dark:text-purple-300',
    description:
      'Ejecuta el modelo prebuilt-invoice de Azure AI Document Intelligence para extraer campos clave y líneas de detalle. Aplica normalización determinista para montos colombianos y CUFE, y resuelve la cuenta bancaria con Azure OpenAI.',
  },
  validate: {
    title: 'Validaciones Deterministas de Normativa',
    subtitle: 'Reglas puras DIAN y consistencia contable',
    technology: 'Reglas Deterministas DIAN (0 ms LLM)',
    tagStyle: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300',
    description:
      'Calcula el Dígito de Verificación del NIT con algoritmo módulo 11 de la DIAN, verifica la suma aritmética de líneas e impuestos con tolerancia de $1 COP, valida longitud/formato de 96 caracteres del CUFE y comprueba coherencia de fechas.',
  },
  match: {
    title: 'Cotejo de 3 Vías (Three-Way Match)',
    subtitle: 'Cruce con Órdenes de Compra y Recepciones en Postgres',
    technology: 'SQL Relacional Determinista',
    tagStyle: 'border-cyan-200 bg-cyan-50 text-cyan-700 dark:border-cyan-900/60 dark:bg-cyan-950/40 dark:text-cyan-300',
    description:
      'Consulta las órdenes de compra en PostgreSQL, compara precios unitarios línea por línea con tolerancia del 2%, y acumula cantidades facturadas históricamente contra las recepciones reales en almacén.',
  },
  risk: {
    title: 'Evaluación de Fraude y Riesgo de Proveedor',
    subtitle: 'Seguridad en pagos y prevención de suplantación',
    tagStyle: 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-300',
    technology: 'Reglas Antifraude',
    description:
      'Comprueba que el proveedor esté registrado y ACTIVO en el maestro. Detecta facturas duplicadas por (NIT, número) y dispara alerta crítica inmediata si la cuenta bancaria impresa difiere de la registrada.',
  },
  decide: {
    title: 'Decisión Ejecutiva y Explicación IA',
    subtitle: 'Matriz determinista + Explicador Azure OpenAI',
    technology: 'Matriz de Negocio + Azure OpenAI',
    tagStyle: 'border-indigo-200 bg-indigo-50 text-indigo-700 dark:border-indigo-900/60 dark:bg-indigo-950/40 dark:text-indigo-300',
    description:
      'Evalúa todos los hallazgos según la matriz de decisión y el umbral de $20M COP. Si hay rechazo, redacta un borrador de correo al proveedor; para el analista, genera una explicación ejecutiva clara en español.',
  },
  human_review: {
    title: 'Pausa Human-in-the-Loop (HITL)',
    subtitle: 'Persistencia de estado con LangGraph PostgresSaver',
    technology: 'LangGraph Checkpointing & Interrupt',
    tagStyle: 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300',
    description:
      'Si la decisión es REVISION, invoca interrupt() pausando la ejecución del pipeline y guardando el checkpoint en PostgreSQL. Espera la confirmación de un analista humano en la cola de revisión para reanudar el grafo.',
  },
}

function formatTime(timestamp: string): string {
  try {
    const d = new Date(timestamp)
    return d.toLocaleTimeString('es-CO', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3,
    })
  } catch {
    return timestamp
  }
}

function NodeIcon({ node }: { node: string }) {
  switch (node) {
    case 'ingest':
      return (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
        </svg>
      )
    case 'extract':
      return (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      )
    case 'validate':
      return (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      )
    case 'match':
      return (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
        </svg>
      )
    case 'risk':
      return (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      )
    case 'decide':
      return (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      )
    case 'human_review':
      return (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
      )
    default:
      return (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      )
  }
}

export function AgentTraceView({ trace, isLoading, decision }: AgentTraceViewProps) {
  const [expandedRunIds, setExpandedRunIds] = useState<Set<string>>(new Set())
  const [copiedRunId, setCopiedRunId] = useState<string | null>(null)

  const toggleExpand = (runId: string) => {
    setExpandedRunIds((prev) => {
      const next = new Set(prev)
      if (next.has(runId)) {
        next.delete(runId)
      } else {
        next.add(runId)
      }
      return next
    })
  }

  const handleCopyJson = (run: AgentRunItem) => {
    if (run.output) {
      navigator.clipboard.writeText(JSON.stringify(run.output, null, 2))
      setCopiedRunId(run.id)
      setTimeout(() => setCopiedRunId(null), 2000)
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900/50">
        <div className="flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
          <span className="h-5 w-5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
          Cargando traza del grafo y agentes...
        </div>
      </div>
    )
  }

  if (!trace || trace.runs.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center shadow-xs dark:border-slate-800 dark:bg-slate-900/50">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <h3 className="mt-4 text-base font-bold text-slate-900 dark:text-slate-100">
          Sin trazas de ejecución registradas
        </h3>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
          Esta factura no cuenta con registros en la tabla <code className="font-mono text-slate-700 dark:text-slate-300">agent_runs</code>.
          Las trazas se registran automáticamente cuando el pipeline procesa la factura con seguimiento activo.
        </p>
      </div>
    )
  }

  const totalTokens = trace.total_tokens_in + trace.total_tokens_out
  const costFormatted = trace.cost_usd ? `$${Number(trace.cost_usd).toFixed(4)} USD` : '—'

  return (
    <div className="space-y-6">
      {/* Trace Metrics Summary Bar */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {/* Total Time */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900/50">
          <span className="text-[11px] font-semibold text-slate-500 uppercase dark:text-slate-400">
            Tiempo Total
          </span>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-xl font-bold text-slate-900 dark:text-slate-100">
              {trace.total_duration_ms < 1000
                ? `${trace.total_duration_ms} ms`
                : `${(trace.total_duration_ms / 1000).toFixed(2)}s`}
            </span>
          </div>
          <span className="text-[10px] text-slate-400">Suma de agentes</span>
        </div>

        {/* Steps count */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900/50">
          <span className="text-[11px] font-semibold text-slate-500 uppercase dark:text-slate-400">
            Agentes
          </span>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-xl font-bold text-brand-600 dark:text-brand-400">
              {trace.runs.length}
            </span>
            <span className="text-xs text-slate-500">nodos</span>
          </div>
          <span className="text-[10px] text-slate-400">Pipeline LangGraph</span>
        </div>

        {/* Tokens */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900/50">
          <span className="text-[11px] font-semibold text-slate-500 uppercase dark:text-slate-400">
            Tokens LLM
          </span>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-xl font-bold text-slate-900 dark:text-slate-100">
              {totalTokens > 0 ? totalTokens.toLocaleString('es-CO') : '0'}
            </span>
          </div>
          <span className="text-[10px] text-slate-400">
            {trace.total_tokens_in} in / {trace.total_tokens_out} out
          </span>
        </div>

        {/* Cost */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900/50">
          <span className="text-[11px] font-semibold text-slate-500 uppercase dark:text-slate-400">
            Costo IA
          </span>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-xl font-bold text-slate-900 dark:text-slate-100">
              {costFormatted}
            </span>
          </div>
          <span className="text-[10px] text-slate-400">Azure OpenAI + Doc Intel</span>
        </div>
      </div>

      {/* Interactive Timeline */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900/50">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
          <div>
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              Línea de Tiempo de Ejecución Multiagente
            </h2>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              Trazabilidad paso a paso de cada nodo en el grafo con tiempos, métricas y datos estructurados de salida.
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              if (expandedRunIds.size === trace.runs.length) {
                setExpandedRunIds(new Set())
              } else {
                setExpandedRunIds(new Set(trace.runs.map((r) => r.id)))
              }
            }}
            className="text-xs font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400"
          >
            {expandedRunIds.size === trace.runs.length ? 'Colapsar todos' : 'Expandir todos'}
          </button>
        </div>

        <div className="relative mt-6 ml-4 border-l-2 border-slate-200 pl-6 space-y-8 dark:border-slate-800">
          {trace.runs.map((run, idx) => {
            const info = NODE_INFO[run.node] || {
              title: run.node,
              subtitle: 'Nodo personalizado',
              technology: 'LangGraph',
              tagStyle: 'border-slate-200 bg-slate-50 text-slate-700',
              description: 'Ejecución del nodo dentro del pipeline.',
            }
            const isInterrupted =
              run.node === 'human_review' &&
              Boolean(run.output?.interrupt || run.output?.status === 'paused_for_review')
            const isExpanded = expandedRunIds.has(run.id)
            const hasTokens = run.tokens_in !== null || run.tokens_out !== null

            return (
              <div key={run.id} className="relative group">
                {/* Timeline Marker Circle */}
                <div
                  className={`absolute -left-[37px] top-1 flex h-8 w-8 items-center justify-center rounded-full border-2 transition-transform group-hover:scale-105 ${
                    isInterrupted
                      ? 'border-amber-400 bg-amber-500 text-white ring-4 ring-amber-100 dark:ring-amber-950/60'
                      : 'border-emerald-400 bg-emerald-500 text-white shadow-xs'
                  }`}
                >
                  <NodeIcon node={run.node} />
                </div>

                {/* Node Card */}
                <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 transition-all hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900/40 dark:hover:border-slate-700">
                  {/* Top Header */}
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-mono font-bold text-slate-400">
                          #{idx + 1}
                        </span>
                        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                          {info.title}
                        </h3>
                        <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${info.tagStyle}`}>
                          {info.technology}
                        </span>
                      </div>
                      <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                        {info.subtitle}
                      </p>
                    </div>

                    {/* Status & Timing Badges */}
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center gap-1 rounded-md bg-slate-200/70 px-2 py-1 text-xs font-mono font-semibold text-slate-800 dark:bg-slate-800 dark:text-slate-200">
                        ⏱️ {run.duration_ms} ms
                      </span>
                      {isInterrupted ? (
                        <span className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-100 px-2.5 py-0.5 text-[11px] font-semibold text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300">
                          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-600" />
                          Pausado (interrupt)
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-100/70 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300">
                          ✓ Completado
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Description */}
                  <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                    {info.description}
                  </p>

                  {/* Execution Meta Bar (Tokens & Timestamp) */}
                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-200/60 pt-2 text-[11px] text-slate-500 dark:border-slate-800/80 dark:text-slate-400">
                    <div className="flex items-center gap-3">
                      <span>Inicio: <span className="font-mono font-medium text-slate-700 dark:text-slate-300">{formatTime(run.started_at)}</span></span>
                      {hasTokens && (
                        <span>
                          Tokens: <span className="font-mono font-medium text-slate-700 dark:text-slate-300">{run.tokens_in ?? 0} in / {run.tokens_out ?? 0} out</span>
                        </span>
                      )}
                    </div>

                    <button
                      type="button"
                      onClick={() => toggleExpand(run.id)}
                      className="inline-flex items-center gap-1 font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400"
                    >
                      <svg
                        className={`h-3.5 w-3.5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                      {isExpanded ? 'Ocultar payload' : 'Ver payload de salida'}
                    </button>
                  </div>

                  {/* Interrupted HITL Callout */}
                  {isInterrupted && (
                    <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs dark:border-amber-900/60 dark:bg-amber-950/40">
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1">
                          <p className="font-bold text-amber-900 dark:text-amber-200">
                            Esperando resolución de analista humano
                          </p>
                          <p className="text-amber-800 dark:text-amber-300">
                            El pipeline detectó hallazgos que requieren aprobación humana (decisión {decision}).
                            El estado completo se conserva en PostgreSQL mediante LangGraph Checkpoint.
                          </p>
                        </div>
                        <Link
                          to="/review"
                          className="shrink-0 rounded-md bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-700"
                        >
                          Ir a Revisar →
                        </Link>
                      </div>
                    </div>
                  )}

                  {/* Expandable JSON Payload Inspector */}
                  {isExpanded && (
                    <div className="mt-3 overflow-hidden rounded-lg border border-slate-800 bg-slate-950">
                      <div className="flex items-center justify-between border-b border-slate-800 px-3 py-1.5 text-[11px] text-slate-400">
                        <span className="font-mono">output: JSON</span>
                        <button
                          type="button"
                          onClick={() => handleCopyJson(run)}
                          className="text-[11px] text-brand-400 hover:text-brand-300 font-medium"
                        >
                          {copiedRunId === run.id ? '✓ ¡Copiado!' : 'Copiar JSON'}
                        </button>
                      </div>
                      <pre className="max-h-72 overflow-auto p-3 font-mono text-[11px] text-emerald-400">
                        {run.output ? JSON.stringify(run.output, null, 2) : 'null'}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
