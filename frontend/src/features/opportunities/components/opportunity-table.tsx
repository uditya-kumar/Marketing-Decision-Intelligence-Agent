import { Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { ConfidenceMeter } from '@/components/common/confidence-meter'
import { PriorityDot } from '@/components/common/priority-dot'
import { ageLabel, channelLabel, impactText, subLine, type Opportunity } from '@/lib/opportunities'
import { cn } from '@/lib/utils'

// Dot · opportunity · channel · impact · confidence · age · chevron.
const COLUMNS = 'grid grid-cols-[8px_minmax(0,1fr)_110px_90px_150px_56px_16px] items-center gap-4'

const HEADINGS = ['OPPORTUNITY', 'CHANNEL', 'IMPACT / WEEK', 'CONFIDENCE', 'AGE']

export function OpportunityTable({ rows }: { rows: Opportunity[] }) {
  return (
    <div className="flex flex-col">
      <div
        className={cn(
          COLUMNS,
          'border-b border-hairline px-4 pb-2.5 font-mono text-[11px] tracking-[0.6px] text-ash',
        )}
      >
        <span />
        {HEADINGS.map((heading) => (
          <span key={heading}>{heading}</span>
        ))}
        <span />
      </div>
      {rows.map((row) => (
        <Link
          key={row.id}
          to={`/opportunities/${row.id}`}
          className={cn(
            COLUMNS,
            'rounded-lg border-b border-hairline px-4 py-[18px] transition-colors duration-150 ease-out hover:bg-bone',
            row.status === 'dismissed' && 'opacity-60',
          )}
        >
          <PriorityDot band={row.band} kind={row.kind} />
          <span className="flex min-w-0 flex-col gap-[3px]">
            <span className="truncate text-[15px] text-ink">{row.title}</span>
            <span className="truncate text-[13px] text-ash">{subLine(row)}</span>
          </span>
          <span className="truncate text-driftwood">{channelLabel(row.channel_id)}</span>
          <span className={row.kind === 'win' ? 'text-verdant' : 'text-ink'}>
            {impactText(row)}
          </span>
          <ConfidenceMeter confidence={row.confidence} />
          <span className="font-mono text-[12px] text-ash">{ageLabel(row.age_days)}</span>
          <ChevronRight className="size-4 text-mist" aria-hidden />
        </Link>
      ))}
    </div>
  )
}
