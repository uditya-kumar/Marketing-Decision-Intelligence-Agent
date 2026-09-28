import { ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  awaitingLine,
  todayLine,
  verdictChip,
  type Experiment,
  type ExperimentsToday,
} from '@/lib/experiments'
import { cn } from '@/lib/utils'

function Row({ children }: { children: React.ReactNode }) {
  return (
    <Link
      to="/experiments"
      className="flex items-center gap-3 border-b border-hairline py-3.5 text-[13px] last:border-b-0 hover:text-ink"
    >
      {children}
      <ChevronRight className="size-4 shrink-0 text-mist" aria-hidden />
    </Link>
  )
}

function Completed({ row }: { row: Experiment }) {
  const chip = row.verdict === null ? null : verdictChip(row.verdict)
  return (
    <Row>
      <span className="min-w-0 flex-1 truncate text-ink">{todayLine(row)}</span>
      {chip && (
        <span className={cn('font-mono text-[11px] tracking-[0.6px] uppercase', chip.className)}>
          {chip.label} ✓
        </span>
      )}
    </Row>
  )
}

/** "Experiments · Creative rotation · Day 4/7 · 1 awaiting approval →" (UI.md §5.1): the last
 *  section of Today, and where Flow D's completed verdict shows up. */
export function ExperimentsStrip({ experiments }: { experiments: ExperimentsToday }) {
  const { running, completed, awaiting } = experiments
  if (running.length === 0 && completed.length === 0 && awaiting === 0) return null
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-[13px] font-normal text-ash">Experiments</h2>
      <div className="flex flex-col rounded-lg border border-hairline bg-bone px-6">
        {completed.map((row) => (
          <Completed key={row.id} row={row} />
        ))}
        {running.map((row) => (
          <Row key={row.id}>
            <span className="min-w-0 flex-1 truncate text-ink">{todayLine(row)}</span>
          </Row>
        ))}
        {awaiting > 0 && (
          <Row>
            <span className="min-w-0 flex-1 truncate text-ember">{awaitingLine(awaiting)}</span>
          </Row>
        )}
      </div>
    </section>
  )
}
