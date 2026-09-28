import { Activity, Lock, TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'
import { ConfidenceMeter } from '@/components/common/confidence-meter'
import { Eyebrow } from '@/components/common/section'
import type { Schemas } from '@/lib/api-client'
import { formatInr, formatShortDate } from '@/lib/format'
import { metricLabel } from '@/lib/metrics'
import { confidenceNote, levelLine, signalLabel, statusLabel } from '@/lib/opportunities'
import { cn } from '@/lib/utils'
import type { OpportunityDetail } from '../api'

const STATUS_DOTS: Record<Schemas['OpportunityOut']['status'], string> = {
  open: 'bg-amber',
  experimenting: 'bg-forest',
  dismissed: 'bg-mist',
  resolved: 'bg-verdant',
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5 border-b border-hairline py-4 last:border-b-0">
      <Eyebrow>{label}</Eyebrow>
      {children}
    </div>
  )
}

/** The right-hand rail: what this is worth, how sure we are, and where it stands. */
export function SummaryRail({ detail }: { detail: OpportunityDetail }) {
  const { summary, signals, trust, protected: isProtected } = detail
  const level = levelLine(summary)
  return (
    <aside className="flex flex-col gap-8">
      <div className="flex flex-col rounded-lg border border-hairline bg-bone px-6 py-2">
        <Row label="Estimated impact">
          <span className="text-heading font-normal text-ink">
            {formatInr(Math.abs(summary.impact), { compact: true })} / week
          </span>
          <span className="text-[12px] text-ash">
            {summary.kind === 'win'
              ? 'what acting on this could add'
              : 'what this costs while it runs'}
          </span>
        </Row>
        <Row label="Confidence">
          <ConfidenceMeter confidence={summary.confidence} />
          <span className="text-[12px] text-ash">
            {confidenceNote(summary.signal_count, trust)}
          </span>
        </Row>
        <Row label={metricLabel(summary.primary_metric)}>
          <span className="flex items-baseline gap-2">
            <span className="text-ink">{level.value}</span>
            <span className="text-[13px] text-ash">{level.note}</span>
          </span>
        </Row>
        <Row label="Status">
          <span className="flex items-center gap-2">
            <span
              className={cn('size-1.5 shrink-0 rounded-full', STATUS_DOTS[summary.status])}
              aria-hidden
            />
            <span className="text-ink">{statusLabel(summary)}</span>
          </span>
          {summary.dismissed_reason && (
            <span className="text-[12px] text-ash">“{summary.dismissed_reason}”</span>
          )}
        </Row>
      </div>

      {(isProtected || trust !== 'ok') && (
        <div className="flex flex-col gap-3">
          {isProtected && (
            <p className="flex gap-2 text-[13px] text-ash">
              <Lock className="mt-0.5 size-3.5 shrink-0 text-driftwood" aria-hidden />
              This campaign is protected, so nothing here will ever suggest pausing it.
            </p>
          )}
          {trust !== 'ok' && (
            <p className="flex gap-2 text-[13px] text-ash">
              <TriangleAlert className="mt-0.5 size-3.5 shrink-0 text-amber" aria-hidden />
              The data behind this failed a trust check, so treat the numbers as provisional.
            </p>
          )}
        </div>
      )}

      <section className="flex flex-col">
        <Eyebrow className="text-ink">Signals · {signals.length}</Eyebrow>
        {signals.map((signal) => (
          <div
            key={signal.id}
            className="flex items-center gap-2.5 border-b border-hairline py-3 last:border-b-0"
          >
            <Activity className="size-3.5 shrink-0 text-ash" aria-hidden />
            <span className="flex-1 text-[13px] text-ink">{signalLabel(signal)}</span>
            <span className="font-mono text-[11px] text-mist">
              {formatShortDate(signal.window.end)}
            </span>
          </div>
        ))}
      </section>
    </aside>
  )
}
