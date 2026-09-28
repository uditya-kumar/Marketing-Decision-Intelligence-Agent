// Wording for opportunity rows, shared by Today and the Opportunities screens.
// Every number comes from the API; nothing here computes one.
import type { Schemas } from '@/lib/api-client'
import { formatInr, formatPercent } from '@/lib/format'
import { formatMetric, metricLabel } from '@/lib/metrics'

export type Opportunity = Schemas['OpportunityOut']
type Detail = Schemas['OpportunityDetailOut']

const CHANNEL_LABELS: Record<string, string> = {
  google_ads: 'Google',
  meta_ads: 'Meta',
  web_analytics: 'Website',
  store_orders: 'Store',
}

// What a movement was measured against, so "up 22%" says up on what.
const AGAINST: Record<string, string> = {
  baseline_change: 'on its usual level',
  goal_breach: 'past your goal',
  funnel_drop: 'on its usual level',
  segment_divergence: 'apart from other segments',
  tracking_break: 'apart from store orders',
}

// What each detector found, in the words the signals list uses.
const FINDINGS: Record<string, string> = {
  baseline_change: 'changed course',
  goal_breach: 'went past your goal',
  funnel_drop: 'dropped in the funnel',
  segment_divergence: 'is out of line with other segments',
  tracking_break: 'stopped matching store orders',
}

const STATUS_LABELS: Record<Opportunity['status'], string> = {
  open: 'Open · awaiting decision',
  experimenting: 'Experiment running',
  dismissed: 'Dismissed',
  resolved: 'Resolved',
}

export type OpportunityFilter = 'all' | 'issues' | 'wins' | 'dismissed'

// "All" means everything still on the table; a dismissed row has its own segment.
const KEEPS: Record<OpportunityFilter, (row: Opportunity) => boolean> = {
  all: (row) => row.status !== 'dismissed',
  issues: (row) => row.status !== 'dismissed' && row.kind === 'issue',
  wins: (row) => row.status !== 'dismissed' && row.kind === 'win',
  dismissed: (row) => row.status === 'dismissed',
}

/** The rows one segment of the Opportunities control shows, in the order they arrived. */
export function filterRows(rows: Opportunity[], filter: OpportunityFilter): Opportunity[] {
  return rows.filter(KEEPS[filter])
}

/** "Meta", or "All channels" for something measured across the account. */
export function channelLabel(channelId: string | null): string {
  if (channelId === null) return 'All channels'
  return CHANNEL_LABELS[channelId] ?? channelId.replace(/_/g, ' ')
}

/** "Today", "1d", "4d": how long this has been going on. */
export function ageLabel(days: number): string {
  return days === 0 ? 'Today' : `${days}d`
}

/** "−₹31K" for an issue, "+₹8K" for a win: money at stake per week, signed by kind. */
export function impactText({ kind, impact }: Opportunity): string {
  const amount = formatInr(Math.abs(impact), { compact: true })
  return `${kind === 'win' ? '+' : '−'}${amount}`
}

/** "CPA ₹610, up 45% on its usual level · Creative fatigue" */
export function subLine(row: Opportunity): string {
  const label = metricLabel(row.primary_metric)
  // A tracking break measures the platform against the store as a ratio, so the level itself
  // isn't a count anyone would recognise; only its movement is worth showing.
  const level =
    row.primary_detector === 'tracking_break'
      ? label
      : `${label} ${formatMetric(row.primary_metric, row.current)},`
  const against = AGAINST[row.primary_detector] ?? 'on its usual level'
  const move =
    row.change_pct === null
      ? against
      : `${row.change_pct > 0 ? 'up' : 'down'} ${formatPercent(Math.abs(row.change_pct))} ${against}`
  const sentence = `${level} ${move}`
  return row.cause_label ? `${sentence} · ${row.cause_label}` : sentence
}

/** The rail's level row. A tracking break measures the platform against the store, so its
 *  "level" is that share of the usual rate rather than a number of sales. */
export function levelLine(row: Opportunity): { value: string; note: string } {
  if (row.primary_detector === 'tracking_break') {
    return {
      value: row.current === null ? '—' : `${formatPercent(row.current * 100)} of usual`,
      note: 'measured against store orders',
    }
  }
  return {
    value: formatMetric(row.primary_metric, row.current),
    note: `was ${formatMetric(row.primary_metric, row.baseline)}`,
  }
}

/** "Likely: creative fatigue", or nothing when no diagnosis was stored. */
export function causeLine(row: Opportunity): string | undefined {
  if (!row.cause_label) return undefined
  return `Likely: ${row.cause_label.toLowerCase()}`
}

export function statusLabel(row: Opportunity): string {
  return STATUS_LABELS[row.status]
}

/** "CPA went past your goal": one signal in a sentence. */
export function signalLabel(signal: Schemas['SignalOut']): string {
  const finding = FINDINGS[signal.detector] ?? 'moved'
  return `${metricLabel(signal.metric)} ${finding}`
}

/** "4 signals": how many detections back this row. */
export function signalsNote(signalCount: number): string {
  return plural(signalCount, 'signal')
}

/** "4 signals · data trusted": what the confidence number rests on. */
export function confidenceNote(signalCount: number, trust: Detail['trust']): string {
  const data =
    trust === 'ok'
      ? 'data trusted'
      : trust === 'warning'
        ? 'data needs a check'
        : 'tracking is broken'
  return `${signalsNote(signalCount)} · ${data}`
}

/** "META ADS · KURTA SALE", the entity trail under the opportunity title. */
export function entityLine(row: Opportunity): string {
  const parts = [channelLabel(row.channel_id), row.entity_name]
  return parts.join(' · ').toUpperCase()
}

function total(rows: Opportunity[]): string {
  return formatInr(
    rows.reduce((sum, row) => sum + Math.abs(row.impact), 0),
    { compact: true },
  )
}

function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? '' : 's'}`
}

/** The answer-first line above the list: what the open rows are worth in a week. */
export function listSummary(rows: Opportunity[]): string {
  const issues = rows.filter((row) => row.kind === 'issue')
  const wins = rows.filter((row) => row.kind === 'win')
  const parts: string[] = []
  if (issues.length > 0) {
    const verb = issues.length === 1 ? 'is' : 'are'
    parts.push(`${plural(issues.length, 'issue')} ${verb} costing about ${total(issues)} a week.`)
  }
  if (wins.length > 0) {
    parts.push(`${plural(wins.length, 'win')} could add ${total(wins)} if you act.`)
  }
  return parts.join(' ')
}

/** "3 things need your attention" — the Today heading (Demo 3). */
export function attentionSummary(rows: Opportunity[]): string {
  if (rows.length === 0) return 'Nothing needs you today.'
  return `${rows.length} ${rows.length === 1 ? 'thing needs' : 'things need'} your attention`
}
