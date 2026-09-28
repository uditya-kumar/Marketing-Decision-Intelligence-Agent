import { Link } from 'react-router-dom'
import { Gauge } from 'lucide-react'
import type { Schemas } from '@/lib/api-client'
import { formatPercent, parseDate } from '@/lib/format'
import { cn } from '@/lib/utils'
import { budgetLine, paceLine, suggestionLine } from '../text'

type PacingView = Schemas['PacingViewOut']

const monthName = new Intl.DateTimeFormat('en-IN', { month: 'long' })

// Bars stop at the track's end even when a channel has spent past its budget.
function width(pct: number): string {
  return `${Math.min(pct, 100)}%`
}

export function PacingCard({ pacing }: { pacing: PacingView }) {
  const { total, month } = pacing
  const overspent = total !== null && total.remaining_budget < 0
  return (
    <section aria-labelledby="pacing-title" className="flex flex-col gap-4">
      <h2 id="pacing-title" className="text-heading-sm font-normal">
        Budget
      </h2>
      {total && month ? (
        <>
          <div className="flex flex-col gap-1">
            <p className="flex items-baseline gap-3">
              <span className={`text-heading-lg ${overspent ? 'text-amber' : 'text-ink'}`}>
                {formatPercent(total.spent_pct)}
              </span>
              <span className="text-[13px] text-ash">
                of {monthName.format(parseDate(month.start))} budget spent
              </span>
            </p>
            <p className="font-mono text-[12px] text-ash">{budgetLine(total)}</p>
          </div>
          <div className="relative h-3.5">
            <div className="absolute inset-x-0 top-[3px] h-2 rounded-full bg-linen">
              <div
                className={cn('h-full rounded-full', overspent ? 'bg-amber' : 'bg-ink')}
                style={{ width: width(total.spent_pct) }}
              />
            </div>
            <div
              className={cn('absolute top-0 h-3.5 w-0.5', overspent ? 'bg-ink' : 'bg-amber')}
              style={{ left: width(total.month_elapsed_pct) }}
              aria-hidden
            />
          </div>
          <p
            className={cn(
              'flex items-center gap-1.5 text-[13px]',
              total.status === 'on_track' ? 'text-ash' : 'text-amber',
            )}
          >
            <Gauge className="size-3.5" aria-hidden />
            {paceLine(total)}
          </p>
          <ul className="flex flex-col gap-2.5">
            {pacing.channels.map(({ channel, label, pacing: channelPacing }) => (
              <li key={channel} className="flex items-center gap-3">
                <span className="w-[84px] shrink-0 text-[13px] text-ink">{label}</span>
                <span className="h-1 flex-1 rounded-full bg-linen">
                  <span
                    className={cn(
                      'block h-full rounded-full',
                      channelPacing.status === 'over' ? 'bg-amber' : 'bg-driftwood',
                    )}
                    style={{ width: width(channelPacing.spent_pct) }}
                  />
                </span>
                <span className="w-12 text-right font-mono text-[12px] text-ash">
                  {formatPercent(channelPacing.spent_pct)}
                </span>
              </li>
            ))}
          </ul>
          {suggestionLine(total) && (
            <p className="font-mono text-[11px] text-ash">{suggestionLine(total)}</p>
          )}
        </>
      ) : (
        <p className="text-[13px] text-ash">
          Add monthly budgets to see whether spend is on course.{' '}
          <Link to="/settings" className="text-ember hover:underline">
            Set budgets
          </Link>
        </p>
      )}
    </section>
  )
}
