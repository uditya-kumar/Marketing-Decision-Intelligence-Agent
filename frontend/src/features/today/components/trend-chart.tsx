import { useState } from 'react'
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis } from 'recharts'
import { SegmentedControl } from '@/components/common/segmented-control'
import type { Schemas } from '@/lib/api-client'
import { formatDate, formatShortDate } from '@/lib/format'
import { formatMetric, metricLabel } from '@/lib/metrics'
import { trendSummary, type TrendMetric } from '../text'

const OPTIONS: { value: TrendMetric; label: string }[] = [
  { value: 'store_revenue', label: 'Revenue' },
  { value: 'spend', label: 'Spend' },
  { value: 'roas', label: 'ROAS' },
  { value: 'cpa', label: 'CPA' },
]
const CURRENT_DAYS = 7

type TrendChartProps = {
  points: Schemas['TrendPointOut'][]
}

export function TrendChart({ points }: TrendChartProps) {
  const [metric, setMetric] = useState<TrendMetric>('store_revenue')
  const recentFrom = points.length - CURRENT_DAYS

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-[13px] font-normal text-ash">
          {metricLabel(metric)} · last {points.length} days
        </h2>
        <SegmentedControl
          label="Trend metric"
          options={OPTIONS}
          value={metric}
          onChange={setMetric}
        />
      </div>
      <div className="h-[164px]" aria-hidden>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={points}
            barCategoryGap={3}
            margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
          >
            <XAxis
              dataKey="date"
              tickFormatter={formatShortDate}
              ticks={[points[0]?.date, points[recentFrom]?.date, points.at(-1)?.date].filter(
                (d): d is string => d !== undefined,
              )}
              tick={{ fontSize: 11, className: 'fill-mist font-mono' }}
              axisLine={false}
              tickLine={false}
              interval={0}
            />
            <Tooltip
              cursor={{ className: 'fill-linen' }}
              labelFormatter={(date) => formatDate(String(date))}
              formatter={(value) => [formatMetric(metric, Number(value)), metricLabel(metric)]}
              contentStyle={{
                background: 'var(--color-parchment)',
                border: '1px solid var(--color-hairline)',
                borderRadius: 4,
                fontSize: 13,
              }}
            />
            <Bar dataKey={metric} radius={[2, 2, 0, 0]} isAnimationActive={false}>
              {points.map((point, index) => (
                <Cell
                  key={point.date}
                  className={index >= recentFrom ? 'fill-ink' : 'fill-stone'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[13px] text-driftwood">{trendSummary(points, metric)}</p>
    </section>
  )
}
