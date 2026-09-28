import { CircleCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ConfidenceMeter } from '@/components/common/confidence-meter'
import { PriorityTag } from '@/components/common/priority-dot'
import { Button } from '@/components/ui/button'
import { signalsNote, subLine, type Opportunity } from '@/lib/opportunities'

/** The calm state: nothing scored high enough to bother the reader with. */
function AllClear() {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-hairline bg-bone px-6 py-5">
      <CircleCheck className="size-4 shrink-0 text-verdant" aria-hidden />
      <p className="text-ink">All clear. Nothing needs you today.</p>
    </div>
  )
}

function AttentionCard({ row }: { row: Opportunity }) {
  return (
    <article className="flex flex-col gap-3 rounded-lg border border-hairline bg-bone p-6">
      <div className="flex items-center gap-3">
        <PriorityTag band={row.band} kind={row.kind} />
        <h3 className="flex-1 text-ink">{row.title}</h3>
      </div>
      <p className="text-[13px] text-driftwood">{subLine(row)}</p>
      <div className="flex items-center gap-4">
        <ConfidenceMeter confidence={row.confidence} />
        <span className="text-[12px] text-ash">{signalsNote(row.signal_count)}</span>
        <span className="flex-1" />
        <Button asChild size="sm">
          <Link to={`/opportunities/${row.id}`}>Review</Link>
        </Button>
        <Button asChild variant="ghost" size="sm">
          <Link to={`/opportunities/${row.id}?dismiss=1`}>Dismiss</Link>
        </Button>
      </div>
    </article>
  )
}

/** "Needs attention · 2" (UI.md §5.1): the open issues worth a decision today. */
export function AttentionList({ rows }: { rows: Opportunity[] }) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-[13px] font-normal text-ash">
        Needs attention{rows.length > 0 && ` · ${rows.length}`}
      </h2>
      {rows.length === 0 ? (
        <AllClear />
      ) : (
        <div className="flex flex-col gap-4">
          {rows.map((row) => (
            <AttentionCard key={row.id} row={row} />
          ))}
        </div>
      )}
    </section>
  )
}
