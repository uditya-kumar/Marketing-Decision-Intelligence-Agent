import type { ReactNode } from 'react'
import { formatInr } from '@/lib/format'
import { metricLabel } from '@/lib/metrics'
import { Eyebrow } from '@/components/common/section'
import type { Recommendation } from '../api'

// Display names for the action catalogue (FR-9.1); the action itself is chosen in the backend.
const ACTIONS: Record<Recommendation['action'], string> = {
  pause_creative: 'Pause this creative',
  rotate_creative: 'Rotate in a fresh creative for the same audience',
  refine_audience: 'Narrow the audience',
  investigate_landing_page: 'Check the landing page for this traffic',
  fix_tracking: 'Fix the tracking before acting on these numbers',
  shift_budget: 'Move budget towards what is working',
  adjust_pacing: 'Adjust the daily spend',
}

const RISKS: Record<Recommendation['risk'], string> = {
  low: 'Low · little to lose',
  medium: 'Medium · watch it closely',
  high: 'High · approve with care',
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1 border-l border-hairline px-4 first:border-l-0 first:pl-0">
      <Eyebrow>{label}</Eyebrow>
      <span className="text-[13px] text-ink">{children}</span>
    </div>
  )
}

type RecommendationCardProps = {
  recommendation: Recommendation
  /** Sits under the facts: Dismiss today, Create experiment once Phase 8 lands. */
  actions?: ReactNode
}

export function RecommendationCard({ recommendation, actions }: RecommendationCardProps) {
  const [low, high] = recommendation.expected_impact
  const params = Object.entries(recommendation.params)
  return (
    <div className="flex flex-col gap-5 rounded-lg border border-hairline bg-bone p-7">
      <div className="flex flex-col gap-2">
        <h3 className="text-heading-sm font-normal text-ink">{ACTIONS[recommendation.action]}</h3>
        <p className="font-serif text-[17px] leading-[1.45] text-driftwood">
          {recommendation.rationale}
        </p>
        {params.length > 0 && (
          <p className="font-mono text-[11px] text-ash">
            {params.map(([key, value]) => `${key} ${value}`).join(' · ')}
          </p>
        )}
      </div>
      <div className="grid grid-cols-4 border-t border-hairline pt-3.5">
        <Fact label="Expected">
          {/* A fix such as repairing tracking earns nothing by itself; the range says so. */}
          {low === 0 && high === 0 ? (
            'No rupee gain on its own'
          ) : (
            <>
              {formatInr(low, { compact: true })}–{formatInr(high, { compact: true })} a week
            </>
          )}
        </Fact>
        <Fact label="Risk">{RISKS[recommendation.risk]}</Fact>
        <Fact label="Watch">{metricLabel(recommendation.watch)}</Fact>
        {/* The computed sentence starts with "Stop if", which the label already says. */}
        <Fact label="Stop if">
          {recommendation.stop_condition.replace(/^Stop if /, '').replace(/\.$/, '')}
        </Fact>
      </div>
      {actions}
    </div>
  )
}
