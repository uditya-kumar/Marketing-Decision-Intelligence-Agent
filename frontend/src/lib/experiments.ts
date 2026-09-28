// Wording for experiment rows, shared by Today and the Experiments screen.
// Every number comes from the API; nothing here computes one.
import { actionName } from '@/lib/actions'
import type { Schemas } from '@/lib/api-client'
import { formatShortDate } from '@/lib/format'
import { formatMetric, metricLabel } from '@/lib/metrics'

export type Experiment = Schemas['ExperimentOut']
export type ExperimentsToday = Schemas['ExperimentsTodayOut']
export type Verdict = NonNullable<Experiment['verdict']>

export type ExperimentTab = 'awaiting' | 'running' | 'completed'

// A rejected change belongs with the finished ones: it is decided, just not tried.
const TABS: Record<ExperimentTab, Experiment['status'][]> = {
  awaiting: ['draft'],
  running: ['running'],
  completed: ['completed', 'rejected'],
}

const VERDICTS: Record<Verdict, { label: string; className: string }> = {
  worked: { label: 'Worked', className: 'text-verdant' },
  did_not_work: { label: "Didn't work", className: 'text-crimson' },
  inconclusive: { label: 'Inconclusive', className: 'text-ash' },
}

/** The rows one tab of the Experiments screen shows, in the order they arrived. */
export function filterExperiments(rows: Experiment[], tab: ExperimentTab): Experiment[] {
  return rows.filter((row) => TABS[tab].includes(row.status))
}

/** The tab to open on: what needs a decision first, else whichever tab has anything to show,
 *  so a verdict is never hidden behind an empty tab. */
export function firstFilledTab(rows: Experiment[]): ExperimentTab {
  const order = Object.keys(TABS) as ExperimentTab[]
  return order.find((tab) => filterExperiments(rows, tab).length > 0) ?? 'awaiting'
}

export function verdictChip(verdict: Verdict): { label: string; className: string } {
  return VERDICTS[verdict]
}

/** "Day 4 of 7": how far a running change has got. */
export function progressText(progress: NonNullable<Experiment['progress']>): string {
  return `Day ${progress.day} of ${progress.total}`
}

/** How full the progress bar is, as a percentage of the duration. */
export function progressPct(progress: NonNullable<Experiment['progress']>): number {
  if (progress.total === 0) return 0
  return Math.min(100, (progress.day / progress.total) * 100)
}

/** "₹610 → ₹420": where the metric was and where it went, or where it should go. */
export function movementText(row: Experiment): string {
  const [from, to] =
    row.status === 'completed' ? [row.before, row.after] : [row.baseline, row.target]
  if (from === null && to === null) return '—'
  return `${formatMetric(row.metric, from)} → ${formatMetric(row.metric, to)}`
}

/** "Watching CPA · 7 days from 15 Oct", the line under a running change. */
export function watchLine(row: Experiment): string {
  const watching = `Watching ${metricLabel(row.metric)}`
  if (row.started_on === null || row.ends_on === null) {
    return `${watching} for ${row.duration_days} days once you approve it`
  }
  return `${watching} · ${formatShortDate(row.started_on)} to ${formatShortDate(row.ends_on)}`
}

/** What a completed change came to, in a sentence: the verdict plus its two readings. */
export function outcomeLine(row: Experiment): string {
  if (row.status === 'rejected') return row.reason ?? 'Turned down, so nothing changed.'
  if (row.verdict === null) return 'Waiting for the week of data that judges it.'
  const days = row.sample_days === null ? '' : ` over ${row.sample_days} days`
  return `${metricLabel(row.metric)} ${movementText(row)}${days}.`
}

/** "Creative rotation · Day 4 of 7" — one experiment on the Today strip (UI.md §5.1).
 *  A completed one reads "Creative rotation completed", with its verdict as the chip. */
export function todayLine(row: Experiment): string {
  const action = actionName(row.action)
  if (row.progress !== null) return `${action} · ${progressText(row.progress)}`
  if (row.status === 'completed') return `${action} completed`
  return action
}

/** "1 awaiting approval": the tail of the Today strip, which links to the tab. */
export function awaitingLine(count: number): string {
  return `${count} awaiting approval`
}

/** The answer-first line above the tabs: what is under way and what came back. */
export function experimentsSummary(rows: Experiment[]): string {
  if (rows.length === 0) return 'Nothing is under test yet.'
  const parts: string[] = []
  const awaiting = filterExperiments(rows, 'awaiting').length
  const running = filterExperiments(rows, 'running').length
  const worked = rows.filter((row) => row.verdict === 'worked').length
  if (awaiting > 0) parts.push(`${plural(awaiting, 'change')} ${verb(awaiting)} waiting on you.`)
  if (running > 0) parts.push(`${plural(running, 'change')} ${verb(running)} being measured.`)
  if (worked > 0) parts.push(`${plural(worked, 'change')} worked.`)
  return parts.join(' ')
}

function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? '' : 's'}`
}

function verb(n: number): string {
  return n === 1 ? 'is' : 'are'
}
