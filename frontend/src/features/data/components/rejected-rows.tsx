import type { Schemas } from '@/lib/api-client'
import { formatCount } from '@/lib/format'

type RejectedRowsProps = {
  rows: Schemas['RejectedRowOut'][]
  total: number
}

/** The row-level errors of one import: which line failed and why. */
export function RejectedRows({ rows, total }: RejectedRowsProps) {
  return (
    <div className="flex flex-col gap-1 rounded-lg bg-bone px-4 py-3">
      <ul className="flex max-h-72 flex-col gap-1 overflow-auto">
        {rows.map((row) => (
          <li key={row.line} className="flex gap-4 font-mono text-[12px]">
            <span className="w-16 shrink-0 text-ash">Line {row.line}</span>
            <span className="text-ink">{row.errors.join(' · ')}</span>
          </li>
        ))}
      </ul>
      {rows.length < total && (
        <p className="pt-1 text-[13px] text-ash">
          Showing the first {formatCount(rows.length)} of {formatCount(total)} rejected rows.
        </p>
      )}
    </div>
  )
}
