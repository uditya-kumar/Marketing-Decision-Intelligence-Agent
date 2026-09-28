import { Delta } from '@/components/common/delta'
import { Eyebrow } from '@/components/common/section'
import type { Schemas } from '@/lib/api-client'
import { formatShortDate } from '@/lib/format'
import { formatMetric } from '@/lib/metrics'
import { signalLabel } from '@/lib/opportunities'

type Signal = Schemas['SignalOut']

const COLUMNS = 'grid grid-cols-[minmax(0,1fr)_150px_140px_80px_90px] items-center gap-4'

/** Every signal this opportunity was grouped from, so the reader can check the working. */
export function SignalsTable({ signals }: { signals: Signal[] }) {
  return (
    <div className="flex flex-col">
      <div className={`${COLUMNS} border-b border-hairline pb-2.5`}>
        <Eyebrow>Signal</Eyebrow>
        <Eyebrow>Where</Eyebrow>
        <Eyebrow>Before → after</Eyebrow>
        <Eyebrow>Change</Eyebrow>
        <Eyebrow>Window</Eyebrow>
      </div>
      {signals.map((signal) => (
        <div key={signal.id} className={`${COLUMNS} border-b border-hairline py-3`}>
          <span className="truncate text-ink">{signalLabel(signal)}</span>
          <span className="truncate text-[13px] text-driftwood">{signal.entity.name}</span>
          <span className="font-mono text-[12px] text-driftwood">
            {formatMetric(signal.metric, signal.baseline)} →{' '}
            {formatMetric(signal.metric, signal.current)}
          </span>
          {/* `adverse` already says whether the move is bad news, whatever the metric's direction. */}
          <Delta
            changePct={signal.change_pct}
            higherIsBetter={
              signal.change_pct === null ? null : signal.change_pct > 0 !== signal.adverse
            }
          />
          <span className="font-mono text-[12px] text-mist">
            {formatShortDate(signal.window.start)} – {formatShortDate(signal.window.end)}
          </span>
        </div>
      ))}
    </div>
  )
}
