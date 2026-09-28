import { ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { impactText, subLine, type Opportunity } from '@/lib/opportunities'

/** "Opportunities · 1" (UI.md §5.1): the upside rows, compact next to Pacing. */
export function WinsList({ rows }: { rows: Opportunity[] }) {
  if (rows.length === 0) return null
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-[13px] font-normal text-ash">Opportunities · {rows.length}</h2>
      <div className="flex flex-col rounded-lg border border-hairline bg-bone px-6">
        {rows.map((row) => (
          <Link
            key={row.id}
            to={`/opportunities/${row.id}`}
            className="flex items-center gap-4 border-b border-hairline py-4 last:border-b-0 hover:text-ink"
          >
            <span className="flex min-w-0 flex-1 flex-col gap-0.5">
              <span className="truncate text-ink">{row.title}</span>
              <span className="truncate text-[13px] text-ash">{subLine(row)}</span>
            </span>
            <span className="shrink-0 text-verdant">{impactText(row)} / week</span>
            <ChevronRight className="size-4 shrink-0 text-mist" aria-hidden />
          </Link>
        ))}
      </div>
    </section>
  )
}
