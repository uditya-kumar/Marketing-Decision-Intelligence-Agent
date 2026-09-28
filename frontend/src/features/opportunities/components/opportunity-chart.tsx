import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis } from 'recharts'
import { Skeleton } from '@/components/ui/skeleton'
import { formatDate, formatShortDate } from '@/lib/format'
import { formatMetric, metricLabel } from '@/lib/metrics'
import type { Opportunity } from '@/lib/opportunities'
import { useOpportunityTrend } from '../api'

/** The primary metric per day, with the opportunity's own window picked out in ink. */
export function OpportunityChart({ row }: { row: Opportunity }) {
  const trend = useOpportunityTrend(row)

  if (trend.isError) {
    return <p className="text-[13px] text-ash">The daily numbers for this one didn't load.</p>
  }
  if (trend.data === null) {
    return (
      <p className="text-[13px] text-ash">
        {metricLabel(row.primary_metric)} isn't broken down by {row.entity_level.replace('_', ' ')}{' '}
        in the imported data, so there's no daily line to show.
      </p>
    )
  }
  if (!trend.data) return <Skeleton className="h-[164px]" />

  const { points } = trend.data
  const inWindow = (date: string) => date >= row.window.start && date <= row.window.end
  const ticks = [points[0]?.date, row.window.start, points.at(-1)?.date].filter(
    (date): date is string => date !== undefined,
  )

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[13px] text-ash">
        {metricLabel(row.primary_metric)} · {trend.data.name} · last {points.length} days
      </p>
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
              ticks={ticks}
              tick={{ fontSize: 11, className: 'fill-mist font-mono' }}
              axisLine={false}
              tickLine={false}
              interval={0}
            />
            <Tooltip
              cursor={{ className: 'fill-linen' }}
              labelFormatter={(date) => formatDate(String(date))}
              formatter={(value) => [
                formatMetric(row.primary_metric, Number(value)),
                metricLabel(row.primary_metric),
              ]}
              contentStyle={{
                background: 'var(--color-parchment)',
                border: '1px solid var(--color-hairline)',
                borderRadius: 4,
                fontSize: 13,
              }}
            />
            <Bar dataKey="value" radius={[2, 2, 0, 0]} isAnimationActive={false}>
              {points.map((point) => (
                <Cell
                  key={point.date}
                  className={inWindow(point.date) ? 'fill-ink' : 'fill-stone'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
