import { formatShortDate } from '@/lib/format'
import { outcomeLine, verdictChip, type Experiment, type Verdict } from '@/lib/experiments'
import { cn } from '@/lib/utils'

/** Worked / Didn't work / Inconclusive, as the chip the Completed tab shows. */
export function VerdictChip({ verdict }: { verdict: Verdict }) {
  const { label, className } = verdictChip(verdict)
  return (
    <span
      className={cn(
        'rounded-lg border border-hairline bg-parchment px-2 py-0.5 font-mono text-[11px] tracking-[0.6px] uppercase',
        className,
      )}
    >
      {label}
    </span>
  )
}

/** The verdict with the before → after behind it, or why there isn't one yet. */
export function Outcome({ experiment }: { experiment: Experiment }) {
  return (
    <div className="flex items-center gap-3 border-t border-hairline pt-5">
      {experiment.verdict !== null && <VerdictChip verdict={experiment.verdict} />}
      {experiment.status === 'rejected' && (
        <span className="font-mono text-[11px] tracking-[0.6px] text-ash uppercase">Rejected</span>
      )}
      <span className="flex-1 text-[13px] text-ink">{outcomeLine(experiment)}</span>
      {experiment.evaluated_on !== null && (
        <span className="font-mono text-[11px] text-mist">
          judged {formatShortDate(experiment.evaluated_on)}
        </span>
      )}
    </div>
  )
}
