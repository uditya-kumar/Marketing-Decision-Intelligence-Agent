// Sentences for the Today screen, built only from numbers the API computed.
import type { Schemas } from '@/lib/api-client'
import { formatDate, formatInr, formatPercent, formatShortDate } from '@/lib/format'
import { formatMetric, metricLabel, type Metric } from '@/lib/metrics'
import { conversionWord, dayCount, shortName } from '@/lib/trust'

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

/** "A", "A and B", "A, B and C" */
function listPhrase(items: string[]): string {
  if (items.length <= 1) return items.join('')
  return `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`
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
  // A goal read off broken tracking isn't worth announcing; the trust banner covers it.
  const behind = today.kpis
    .filter((k) => k.reliable && k.goal?.status === 'behind')
    .map((k) => metricLabel(k.metric))
  if (behind.length > 0) {
    parts.push(`${listPhrase(behind)} ${behind.length === 1 ? 'is' : 'are'} off goal.`)
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

type SourceTrust = Schemas['SourceTrustOut']
type Pacing = Schemas['PacingOut']

// Store orders moving less than this read as "normal" next to a collapsed conversion count.
const STEADY_PCT = 10

const ALERT_RANK: Record<SourceTrust['status'], number> = { broken: 0, warning: 1, ok: 2 }

function movement(pct: number | null): string {
  if (pct === null || Math.abs(pct) < STEADY_PCT) return 'normal'
  return `${pct > 0 ? 'up' : 'down'} ${formatPercent(Math.abs(pct))}`
}

function trackingAlert(source: SourceTrust, muted: string[]): { title: string; body: string } {
  const name = shortName(source.source)
  const tracking = source.tracking
  const since = tracking?.since ? ` since ${formatShortDate(tracking.since)}` : ''
  const reported =
    `${name} reports ${conversionWord(source.source)} ${movement(tracking?.conversions_change_pct ?? null)}` +
    ` while store orders are ${movement(tracking?.orders_change_pct ?? null)}.`
  if (tracking?.status === 'broken') {
    const mutedNote =
      muted.length > 0
        ? ` ${listPhrase(muted)} ${muted.length === 1 ? 'is' : 'are'} greyed out meanwhile.`
        : ''
    return {
      title: `${name} tracking looks broken${since}`,
      body: `${reported} Don't change ${name} campaigns until tracking is fixed.${mutedNote}`,
    }
  }
  return {
    title: `${name} may be under-reporting ${conversionWord(source.source)}${since}`,
    body: `${reported} Check the tracking before acting on ${name} ROAS or CPA.`,
  }
}

function freshnessAlert(source: SourceTrust, asOf: string | null): { title: string; body: string } {
  const { days_behind, missing_dates } = source.freshness
  if (days_behind > 0) {
    const through = asOf
      ? ` Numbers stop at ${formatDate(asOf)}, the last day every source covers.`
      : ''
    return {
      title: `${source.label} is ${dayCount(days_behind)} behind`,
      body: `Upload the latest ${source.label} export to catch up.${through}`,
    }
  }
  const days = missing_dates.slice(0, 3).map(formatShortDate).join(', ')
  const more = missing_dates.length > 3 ? ' and more' : ''
  return {
    title: `${source.label} is missing ${dayCount(missing_dates.length)}`,
    body: `Totals that include ${days}${more} are incomplete. Re-upload the export covering those days.`,
  }
}

/** The Today trust banner: the worst data problem, or nothing when every source is fine. */
export function trustAlert(
  today: Schemas['TodayOut'],
): { title: string; body: string } | undefined {
  // Sources with no data at all are the empty state's job, not the banner's.
  const issues = today.trust.sources
    .filter((s) => s.status !== 'ok' && s.freshness.last_date !== null)
    .sort((a, b) => ALERT_RANK[a.status] - ALERT_RANK[b.status])
  if (issues.length === 0) return undefined
  const [source] = issues
  const muted = today.kpis.filter((k) => !k.reliable).map((k) => metricLabel(k.metric))
  const alert =
    source.tracking && source.tracking.status !== 'ok'
      ? trackingAlert(source, muted)
      : freshnessAlert(source, today.as_of_date)
  const others = issues.length - 1
  if (others === 0) return alert
  const also = ` ${others} other ${others === 1 ? 'source needs' : 'sources need'} a look too.`
  return { ...alert, body: alert.body + also }
}

const PACE_WORDS: Record<Pacing['status'], string> = {
  over: 'Over pace',
  under: 'Under pace',
  on_track: 'On pace',
}

/** "₹14.4L of ₹14.2L · ₹24.8K over", or "… · ₹5.4L left" while budget remains. */
export function budgetLine(pacing: Pacing): string {
  const spent = formatInr(pacing.spent, { compact: true })
  const budget = formatInr(pacing.budget, { compact: true })
  const gap = formatInr(Math.abs(pacing.remaining_budget), { compact: true })
  return `${spent} of ${budget} · ${gap} ${pacing.remaining_budget < 0 ? 'over' : 'left'}`
}

/** "Over pace · 45% of month gone" */
export function paceLine(pacing: Pacing): string {
  return `${PACE_WORDS[pacing.status]} · ${formatPercent(pacing.month_elapsed_pct)} of month gone`
}

/** "Suggested ₹11K/day to land on plan · now ₹16K/day"; nothing on the month's last day. */
export function suggestionLine(pacing: Pacing): string | undefined {
  if (pacing.suggested_daily === null) return undefined
  const now = formatInr(pacing.daily_run_rate, { compact: true })
  if (pacing.suggested_daily === 0) return `Budget used up · now ${now}/day`
  const suggested = formatInr(pacing.suggested_daily, { compact: true })
  return `Suggested ${suggested}/day to land on plan · now ${now}/day`
}
