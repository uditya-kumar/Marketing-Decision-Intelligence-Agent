import { CircleCheck, CircleX, TriangleAlert } from 'lucide-react'
import type { Schemas } from '@/lib/api-client'
import { formatCount } from '@/lib/format'

type Run = Schemas['IngestionRunOut']

/** Icon + text, so the outcome never depends on colour alone. */
export function RunStatus({ run }: { run: Run }) {
  if (run.status === 'failed') {
    return (
      <span className="flex items-center gap-1.5 text-[13px] text-crimson">
        <CircleX className="size-3.5" aria-hidden />
        Not imported
      </span>
    )
  }
  if (run.status === 'partial') {
    const rows = run.rows_rejected === 1 ? 'row needs' : 'rows need'
    return (
      <span className="flex items-center gap-1.5 text-[13px] text-amber">
        <TriangleAlert className="size-3.5" aria-hidden />
        {formatCount(run.rows_rejected)} {rows} attention
      </span>
    )
  }
  return (
    <span className="flex items-center gap-1.5 text-[13px] text-forest">
      <CircleCheck className="size-3.5" aria-hidden />
      Imported
    </span>
  )
}
