import { Link } from 'react-router-dom'

import { LINKEDIN_URL, REPO_URL } from '../lib/constants'

const PIPELINE_STEPS = [
  { name: 'Ingesta', detail: 'Hash y detección de escaneo' },
  { name: 'Extractor', detail: 'Doc Intelligence + normalización' },
  { name: 'Validador', detail: 'NIT, aritmética, CUFE, fechas' },
  { name: 'Conciliador', detail: 'Orden de compra y recepción' },
  { name: 'Riesgo', detail: 'Duplicados y fraude' },
  { name: 'Decisor', detail: 'Aprobar, revisar o rechazar' },
]

const TARGET_METRICS = [
  { label: 'Precisión de extracción', value: '≥ 95 %' },
  { label: 'Decisión correcta vs. ground truth', value: '≥ 90 %' },
  { label: 'Tiempo por factura', value: '< 20 s' },
  { label: 'Costo por factura', value: '< USD 0,02' },
]

export function Landing() {
  return (
    <div className="flex flex-col gap-20">
      <section className="flex flex-col items-center gap-6 py-10 text-center">
        <span className="rounded-full bg-brand-50 px-3 py-1 text-sm font-medium text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
          Cuentas por pagar con IA
        </span>
        <h1 className="max-w-3xl text-4xl font-bold tracking-tight text-balance sm:text-5xl">
          Automatización inteligente de cuentas por pagar
        </h1>
        <p className="max-w-2xl text-lg text-slate-600 dark:text-slate-300">
          RPA para capturar las facturas, IA para entenderlas y reglas deterministas para
          decidir. Procesa una factura en segundos con trazabilidad completa de cada decisión.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/upload"
            className="rounded-lg bg-brand-600 px-5 py-2.5 font-medium text-white transition hover:bg-brand-700"
          >
            Probar con una factura de ejemplo
          </Link>
          <a
            href={REPO_URL}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg border border-slate-300 px-5 py-2.5 font-medium text-slate-700 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-900"
          >
            Ver el repositorio
          </a>
        </div>
      </section>

      <section className="flex flex-col gap-6">
        <h2 className="text-center text-2xl font-semibold">Cómo funciona</h2>
        <div className="flex flex-wrap items-stretch justify-center gap-3">
          {PIPELINE_STEPS.map((step, index) => (
            <div key={step.name} className="flex items-center gap-3">
              <div className="w-36 rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm dark:border-slate-800 dark:bg-slate-900">
                <p className="text-sm font-semibold">{step.name}</p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{step.detail}</p>
              </div>
              {index < PIPELINE_STEPS.length - 1 && (
                <span className="hidden text-slate-300 sm:inline dark:text-slate-700" aria-hidden>
                  →
                </span>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {TARGET_METRICS.map((metric) => (
          <div
            key={metric.label}
            className="rounded-xl border border-slate-200 p-4 text-center dark:border-slate-800"
          >
            <p className="text-2xl font-bold text-brand-600 dark:text-brand-400">{metric.value}</p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{metric.label}</p>
          </div>
        ))}
      </section>

      <footer className="flex flex-col items-center gap-2 border-t border-slate-200 pt-8 text-sm text-slate-500 dark:border-slate-800 dark:text-slate-400">
        <p>Proyecto de portafolio de Sebastián — datos de prueba ficticios.</p>
        <div className="flex gap-4">
          <a href={REPO_URL} target="_blank" rel="noreferrer" className="hover:text-brand-600 dark:hover:text-brand-400">
            GitHub
          </a>
          <a
            href={LINKEDIN_URL}
            target="_blank"
            rel="noreferrer"
            className="hover:text-brand-600 dark:hover:text-brand-400"
          >
            LinkedIn
          </a>
        </div>
      </footer>
    </div>
  )
}
