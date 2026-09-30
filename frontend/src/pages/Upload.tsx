import { Dropzone } from '../components/Dropzone'
import { useInvoiceUploads } from '../hooks/useInvoiceUploads'
import { GRAPH_NODES, NODE_LABELS, type Decision } from '../types/processing'

const DECISION_STYLES: Record<Decision, string> = {
  APROBAR: 'bg-green-50 text-decision-aprobar dark:bg-green-900/20',
  REVISION: 'bg-amber-50 text-decision-revision dark:bg-amber-900/20',
  RECHAZAR: 'bg-red-50 text-decision-rechazar dark:bg-red-900/20',
}

export function Upload() {
  const { uploads, addFiles } = useInvoiceUploads()

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold">Subir factura</h1>
        <p className="mt-1 text-slate-500 dark:text-slate-400">
          Sube una o varias facturas en PDF y seguí el avance de cada agente en vivo.
        </p>
      </div>

      <Dropzone onFiles={addFiles} />

      {uploads.length > 0 && (
        <ul className="flex flex-col gap-3">
          {uploads.map((upload) => (
            <li
              key={upload.key}
              className="rounded-xl border border-slate-200 p-4 dark:border-slate-800"
            >
              <div className="flex items-center justify-between gap-3">
                <p className="font-medium">{upload.fileName}</p>
                {upload.decision && (
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold ${DECISION_STYLES[upload.decision]}`}
                  >
                    {upload.decision}
                  </span>
                )}
              </div>

              {upload.status === 'error' ? (
                <p className="mt-2 text-sm text-red-600 dark:text-red-400">
                  {upload.error ?? 'Ocurrió un error al procesar la factura.'}
                </p>
              ) : (
                <ol className="mt-3 flex flex-wrap items-center gap-x-1 gap-y-2 text-sm">
                  {GRAPH_NODES.map((node, index) => {
                    const done = upload.completedNodes.includes(node)
                    return (
                      <li key={node} className="flex items-center gap-1">
                        <span
                          className={
                            done
                              ? 'text-brand-600 dark:text-brand-400'
                              : 'text-slate-400 dark:text-slate-600'
                          }
                        >
                          {NODE_LABELS[node]} {done ? '✓' : ''}
                        </span>
                        {index < GRAPH_NODES.length - 1 && (
                          <span className="text-slate-300 dark:text-slate-700" aria-hidden>
                            →
                          </span>
                        )}
                      </li>
                    )
                  })}
                </ol>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
