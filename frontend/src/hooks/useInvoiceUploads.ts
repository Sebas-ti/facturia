import { useCallback, useState } from 'react'

import { invoiceEventsUrl, uploadInvoice } from '../lib/api'
import type { Decision, GraphNode, UploadItem } from '../types/processing'

interface ProgressEventData {
  node: GraphNode
}

interface DoneEventData {
  status: 'PROCESSED' | 'ERROR'
  decision: Decision | null
}

interface ErrorEventData {
  detail: string
}

export function useInvoiceUploads() {
  const [uploads, setUploads] = useState<UploadItem[]>([])

  const updateUpload = useCallback((key: string, patch: Partial<UploadItem>) => {
    setUploads((current) => current.map((u) => (u.key === key ? { ...u, ...patch } : u)))
  }, [])

  const trackInvoice = useCallback(
    (key: string, invoiceId: string) => {
      const source = new EventSource(invoiceEventsUrl(invoiceId))

      source.addEventListener('progress', (event) => {
        const data = JSON.parse((event as MessageEvent<string>).data) as ProgressEventData
        setUploads((current) =>
          current.map((u) =>
            u.key === key && !u.completedNodes.includes(data.node)
              ? { ...u, completedNodes: [...u.completedNodes, data.node] }
              : u,
          ),
        )
      })

      source.addEventListener('done', (event) => {
        const data = JSON.parse((event as MessageEvent<string>).data) as DoneEventData
        updateUpload(key, {
          status: data.status === 'ERROR' ? 'error' : 'done',
          decision: data.decision ?? undefined,
        })
        source.close()
      })

      source.addEventListener('error', (event) => {
        // A server-sent "event: error" arrives as a MessageEvent with
        // `.data`; a real connection drop arrives as a plain Event without it.
        let detail = 'Se perdió la conexión con el servidor.'
        const data = (event as Partial<MessageEvent<string>>).data
        if (typeof data === 'string') {
          try {
            detail = (JSON.parse(data) as ErrorEventData).detail
          } catch {
            // malformed payload — keep the default message
          }
        }
        updateUpload(key, { status: 'error', error: detail })
        source.close()
      })
    },
    [updateUpload],
  )

  const addFiles = useCallback(
    (files: FileList | File[]) => {
      for (const file of Array.from(files)) {
        const key = `${file.name}-${crypto.randomUUID()}`
        setUploads((current) => [
          ...current,
          { key, fileName: file.name, status: 'uploading', completedNodes: [] },
        ])

        uploadInvoice(file)
          .then(({ invoiceId }) => {
            updateUpload(key, { status: 'processing', invoiceId })
            trackInvoice(key, invoiceId)
          })
          .catch((error: unknown) => {
            const message = error instanceof Error ? error.message : 'Error al subir la factura.'
            updateUpload(key, { status: 'error', error: message })
          })
      }
    },
    [trackInvoice, updateUpload],
  )

  return { uploads, addFiles }
}
