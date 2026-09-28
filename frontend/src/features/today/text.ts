// Sentences for the Today screen, built only from numbers the API computed.
import type { Schemas } from '@/lib/api-client'
import { formatDate, formatInr, formatPercent, formatShortDate } from '@/lib/format'
import { formatMetric, metricLabel, type Metric } from '@/lib/metrics'

type Kpi = Schemas['KpiSummaryOut']
type Status = Schemas['GoalOut']['status']

// Status words read differently for a cost limit and a floor like break-even.
const STATUS_WORDS: Partial<Record<Metric, Record<Status, string>>> = {
  cpa: { ahead: 'well within', on_track: 'near the limit', behind: 'over the limit' },
  mer: { ahead: 'above', on_track: 'near', behind: 'below' },
}
const DEFAULT_WORDS: Record<Status, string> = {
  ahead: 'ahead',
  on_track: 'on track',
  behind: 'behind',
}

/** The goal marker under a KPI, e.g. "Target 3.5× · on track". */
export function goalLine(kpi: Kpi): string | undefined {
  if (!kpi.goal) return undefined
  const target = formatMetric(kpi.metric, kpi.goal.target, true)
  const status = (STATUS_WORDS[kpi.metric] ?? DEFAULT_WORDS)[kpi.goal.status]
  switch (kpi.metric) {
    case 'store_revenue':
      return `Goal ${target} · ${status}`
    case 'mer':
      return `Break-even ${target} · ${status}`
    case 'cpa':
      return `Limit ${target} · ${status}`
    default:
      return `Target ${target} · ${status}`
  }
}

export function greeting(now: Date): string {
  const hour = now.getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

/** The answer-first line: how revenue moved and how many goals are slipping. */
export function weekSummary(today: Schemas['TodayOut']): string {
  const revenue = today.kpis.find((k) => k.metric === 'store_revenue')
  const end = today.period ? ` in the week to ${formatDate(today.period.end)}` : ''
  const parts: string[] = []
  if (revenue?.value != null) {
    const change =
      revenue.change_pct == null
        ? ''
        : `, ${revenue.change_pct >= 0 ? 'up' : 'down'} ${formatPercent(Math.abs(revenue.change_pct))} on the week before`
    parts.push(`Revenue was ${formatInr(revenue.value, { compact: true })}${end}${change}.`)
  }
  const behind = today.kpis
    .filter((k) => k.goal?.status === 'behind')
    .map((k) => metricLabel(k.metric))
  if (behind.length > 0) {
    parts.push(`${behind.join(' and ')} ${behind.length === 1 ? 'is' : 'are'} off goal.`)
  } else if (today.kpis.some((k) => k.goal)) {
    parts.push('Every goal is on track.')
  }
  return parts.join(' ')
}

export type TrendMetric = 'store_revenue' | 'spend' | 'roas' | 'cpa'

/** One-line text version of the trend chart, for screen readers and quick reading. */
export function trendSummary(points: Schemas['TrendPointOut'][], metric: TrendMetric): string {
  const days = points.flatMap(({ date, [metric]: value }) =>
    value === null ? [] : [{ date, value }],
  )
  if (days.length === 0) return `No ${metricLabel(metric)} recorded in the last 30 days.`
  const high = days.reduce((a, b) => (b.value > a.value ? b : a))
  const low = days.reduce((a, b) => (b.value < a.value ? b : a))
  return (
    `Highest on ${formatShortDate(high.date)} (${formatMetric(metric, high.value, true)}), ` +
    `lowest on ${formatShortDate(low.date)} (${formatMetric(metric, low.value, true)}). ` +
    'Dark bars are the last 7 days.'
  )
}
