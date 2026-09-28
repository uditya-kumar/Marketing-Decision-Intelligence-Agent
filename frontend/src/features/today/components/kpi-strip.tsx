import { KpiCard } from '@/components/common/kpi-card'
import type { Schemas } from '@/lib/api-client'
import { formatMetric, metricLabel } from '@/lib/metrics'
import { cn } from '@/lib/utils'
import { goalLine } from '../text'

export function KpiStrip({ kpis }: { kpis: Schemas['KpiSummaryOut'][] }) {
  return (
    <section
      aria-label="This week's key numbers"
      className="grid grid-cols-5 border-y border-hairline"
    >
      {kpis.map((kpi, index) => (
        <KpiCard
          key={kpi.metric}
          className={cn('px-6 py-5', index === 0 ? 'pl-0' : 'border-l border-hairline')}
          label={metricLabel(kpi.metric)}
          value={formatMetric(kpi.metric, kpi.value, true)}
          changePct={kpi.change_pct}
          higherIsBetter={kpi.higher_is_better}
          comparison="vs last week"
          goal={kpi.reliable ? goalLine(kpi) : 'Unreliable while tracking is broken'}
          muted={!kpi.reliable}
        />
      ))}
    </section>
  )
}
