import { useRef, useState, type DragEvent } from 'react'
import { FileUp, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useUpload } from '../api'
import { RunRow } from './run-row'

type UploadZoneProps = {
  sourceLabels: Record<string, string>
}

function kilobytes(bytes: number): string {
  return `${Math.max(1, Math.round(bytes / 1024))} KB`
}

/** Drop or pick CSV exports, then import them; each file reports its detected source. */
export function UploadZone({ sourceLabels }: UploadZoneProps) {
  const input = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<File[]>([])
  const [dragging, setDragging] = useState(false)
  const upload = useUpload()

  function add(picked: FileList | null) {
    const csvs = Array.from(picked ?? []).filter((f) => f.name.toLowerCase().endsWith('.csv'))
    upload.reset()
    setFiles((current) => [...current.filter((f) => !csvs.some((c) => c.name === f.name)), ...csvs])
  }

  function onDrop(event: DragEvent) {
    event.preventDefault()
    setDragging(false)
    add(event.dataTransfer.files)
  }

  function importFiles() {
    upload.mutate(files, { onSuccess: () => setFiles([]) })
  }

  return (
    <section className="flex flex-col rounded-lg border border-stone bg-bone">
      <div
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          'flex flex-col items-center gap-3 px-6 py-9 text-center transition-colors duration-150 ease-out',
          dragging && 'bg-linen',
        )}
      >
        <span className="flex size-10 items-center justify-center rounded-lg bg-linen">
          <FileUp className="size-5 text-ash" aria-hidden />
        </span>
        <p className="text-ink">
          Drop CSV files here, or{' '}
          <button
            type="button"
            className="text-ember hover:underline"
            onClick={() => input.current?.click()}
          >
            browse
          </button>
        </p>
        <p className="text-[13px] text-ash">
          Google Ads, Meta Ads, web analytics and store orders. Each file is matched to its source
          by its columns.
        </p>
        <input
          ref={input}
          type="file"
          accept=".csv,text/csv"
          multiple
          hidden
          onChange={(event) => {
            add(event.target.files)
            event.target.value = ''
          }}
        />
      </div>

      {files.length > 0 && (
        <ul className="border-t border-stone bg-parchment">
          {files.map((file) => (
            <li
              key={file.name}
              className="flex items-center gap-4 border-b border-hairline px-5 py-3.5 last:border-b-0"
            >
              <span className="flex-1 font-mono text-[12px] text-ink">{file.name}</span>
              <span className="text-[13px] text-ash">{kilobytes(file.size)}</span>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label={`Remove ${file.name}`}
                onClick={() => setFiles(files.filter((f) => f !== file))}
              >
                <X aria-hidden />
              </Button>
            </li>
          ))}
        </ul>
      )}

      {upload.data && (
        <ul className="border-t border-stone bg-parchment px-5">
          {upload.data.runs.map((run) => (
            <RunRow
              key={run.id}
              run={run}
              sourceLabel={run.source ? sourceLabels[run.source] : undefined}
              lead={<span className="font-mono text-[12px] text-ink">{run.file_name}</span>}
            />
          ))}
        </ul>
      )}

      {upload.isError && (
        <p role="alert" className="border-t border-stone px-5 py-3.5 text-[13px] text-crimson">
          {upload.error.message}
        </p>
      )}

      {files.length > 0 && (
        <div className="flex items-center gap-3 border-t border-stone px-5 py-3.5">
          <p className="flex-1 text-[13px] text-ash">
            Rows already imported for the same day are replaced, not duplicated.
          </p>
          <Button variant="ghost" onClick={() => setFiles([])} disabled={upload.isPending}>
            Clear
          </Button>
          <Button onClick={importFiles} disabled={upload.isPending}>
            {upload.isPending ? 'Importing…' : `Import ${files.length === 1 ? 'file' : 'files'}`}
          </Button>
        </div>
      )}
    </section>
  )
}
