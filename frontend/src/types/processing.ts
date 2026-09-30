// Mirrors backend/app/graph.py's GRAPH_NODE_ORDER.
export const GRAPH_NODES = [
  'ingest',
  'extract',
  'validate',
  'match',
  'risk',
  'decide',
  'human_review',
] as const

export type GraphNode = (typeof GRAPH_NODES)[number]

export const NODE_LABELS: Record<GraphNode, string> = {
  ingest: 'Ingesta',
  extract: 'Extracción',
  validate: 'Validación',
  match: 'Conciliación',
  risk: 'Riesgo',
  decide: 'Decisión',
  human_review: 'Revisión humana',
}

export type Decision = 'APROBAR' | 'REVISION' | 'RECHAZAR'

export type UploadStatus = 'uploading' | 'processing' | 'done' | 'error'

export interface UploadItem {
  key: string
  fileName: string
  status: UploadStatus
  invoiceId?: string
  completedNodes: GraphNode[]
  decision?: Decision
  error?: string
}
