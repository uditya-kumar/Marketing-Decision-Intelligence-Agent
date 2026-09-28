import { Link } from 'react-router-dom'
import { formatInr, formatShortDate } from '@/lib/format'
import { decisionLine, type Decision } from '@/lib/decisions'
import { movementText, verdictChip } from '@/lib/experiments'
import { entityLine } from '@/lib/opportunities'
import { cn } from '@/lib/utils'

/** The outcome chip: how the change it led to turned out, if it has been judged. */
function Outcome({ experiment }: { experiment: NonNullable<Decision['experiment']> }) {
  if (experiment.verdict === null) {
    const waiting = experiment.status === 'running' ? 'Measuring' : 'No outcome'
    return <span className="font-mono text-[11px] tracking-[0.6px] text-mist">{waiting}</span>
  }
  const { label, className } = verdictChip(experiment.verdict)
  return (
    <span className="flex items-center gap-2 text-[13px]">
      <span className={cn('font-mono text-[11px] tracking-[0.6px] uppercase', className)}>
        {label}
      </span>
      <span className="text-ash">{movementText(experiment)}</span>
    </span>
  )
}

/** One entry of the timeline: the date, the call, its reason and how it turned out. */
export function DecisionEntry({ entry }: { entry: Decision }) {
  return (
    <article className="flex gap-6 border-b border-hairline py-5 last:border-b-0">
      <span className="w-20 shrink-0 font-mono text-[11px] tracking-[0.6px] text-ash uppercase">
        {formatShortDate(entry.at)}
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <span className="text-ink">{decisionLine(entry)}</span>
        {entry.reason && (
          <p className="font-serif text-[15px] leading-[1.45] text-driftwood">"{entry.reason}"</p>
        )}
        <span className="font-mono text-[11px] tracking-[0.6px] text-mist">
          {entityLine(entry.opportunity)}
        </span>
        <div className="flex items-center gap-4 text-[13px]">
          <Link
            to={`/opportunities/${entry.opportunity.id}`}
            className="text-ember hover:underline"
          >
            The opportunity
          </Link>
          {entry.experiment && (
            <Link to="/experiments" className="text-ember hover:underline">
              The experiment
            </Link>
          )}
        </div>
      </div>
      <div className="flex w-52 shrink-0 flex-col items-end gap-1.5">
        {entry.experiment ? (
          <Outcome experiment={entry.experiment} />
        ) : (
          <span className="font-mono text-[11px] tracking-[0.6px] text-mist">Set aside</span>
        )}
        {entry.impact !== null && (
          <span className="text-[13px] text-ash">
            {formatInr(Math.abs(entry.impact), { compact: true })} a week at stake
          </span>
        )}
      </div>
    </article>
  )
}
