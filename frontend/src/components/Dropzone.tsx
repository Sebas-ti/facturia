import { useCallback, useRef, useState, type DragEvent, type KeyboardEvent } from 'react'

interface DropzoneProps {
  onFiles: (files: FileList) => void
}

export function Dropzone({ onFiles }: DropzoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault()
      setIsDragging(false)
      if (event.dataTransfer.files.length > 0) onFiles(event.dataTransfer.files)
    },
    [onFiles],
  )

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      inputRef.current?.click()
    }
  }

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault()
        setIsDragging(true)
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-label="Subir facturas en PDF"
      className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-12 text-center transition ${
        isDragging
          ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20'
          : 'border-slate-300 hover:border-brand-400 dark:border-slate-700'
      }`}
    >
      <p className="font-medium">Arrastra tus facturas en PDF aquí</p>
      <p className="text-sm text-slate-500 dark:text-slate-400">
        o hacé clic para elegir archivos (máx. 5 MB c/u)
      </p>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        multiple
        className="hidden"
        onChange={(event) => {
          if (event.target.files) {
            onFiles(event.target.files)
            event.target.value = ''
          }
        }}
      />
    </div>
  )
}
