import { useState, type ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import type { Schemas } from '@/lib/api-client'
import { formatCount } from '@/lib/format'
import { RejectedRows } from './rejected-rows'
import { RunStatus } from './run-status'

type Run = Schemas['IngestionRunOut']

type RunRowProps = {
  run: Run
  sourceLabel?: string
  /** Left-hand cell: the file name for fresh uploads, the time for run history. */
  lead: ReactNode
}

/** One imported file: detected source, row counts, outcome and its rejected rows on demand. */
export function RunRow({ run, sourceLabel, lead }: RunRowProps) {
  const [open, setOpen] = useState(false)
  return (
    <li className="flex flex-col gap-3 border-b border-hairline py-3.5 last:border-b-0">
      <div className="flex items-center gap-4">
        <div className="w-56 shrink-0">{lead}</div>
        <span className="w-44 shrink-0">
          {sourceLabel ? (
            <span className="rounded-lg bg-linen whitespace-nowrap px-2 py-[3px] text-[12px] text-ink">
              {sourceLabel}
            </span>
          ) : (
            <span className="text-[13px] text-ash">Unrecognised</span>
          )}
        </span>
        <span className="w-44 shrink-0 text-[13px] text-ash">
          {formatCount(run.rows_accepted)} of {formatCount(run.rows_total)} rows
        </span>
        <span className="flex-1">
          <RunStatus run={run} />
        </span>
        {run.rejected_rows.length > 0 && (
          <Button
            variant="link"
            className="h-auto p-0 font-normal text-ember"
            onClick={() => setOpen(!open)}
            aria-expanded={open}
          >
            {open ? 'Hide rejected rows' : 'View rejected rows'}
          </Button>
        )}
      </div>
      {run.error && <p className="text-[13px] text-crimson">{run.error}</p>}
      {open && <RejectedRows rows={run.rejected_rows} total={run.rows_rejected} />}
    </li>
  )
}
