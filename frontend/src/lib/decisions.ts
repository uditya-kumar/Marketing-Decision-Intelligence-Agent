// Wording for the decision log: what was decided, and how the month it sits in reads.
import type { Schemas } from '@/lib/api-client'
import { actionName } from '@/lib/actions'
import { parseDate } from '@/lib/format'

export type Decision = Schemas['DecisionOut']

const KINDS: Record<Decision['kind'], string> = {
  approve: 'Approved',
  reject: 'Rejected',
  dismiss: 'Dismissed',
}

export function decisionLabel(kind: Decision['kind']): string {
  return KINDS[kind]
}

/** "Approved: rotate in a fresh creative", or the opportunity itself for a dismissal. */
export function decisionLine(entry: Decision): string {
  const label = decisionLabel(entry.kind)
  if (entry.experiment === null) return `${label}: ${entry.opportunity.title}`
  return `${label}: ${actionName(entry.experiment.action).toLowerCase()}`
}

/** "October 2026": the heading the timeline groups under. */
export function monthLabel(iso: string): string {
  return parseDate(iso).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })
}

export type DecisionMonth = { month: string; entries: Decision[] }

/** The log split into months, newest first, keeping the order the API sent. */
export function groupByMonth(entries: Decision[]): DecisionMonth[] {
  const months: DecisionMonth[] = []
  for (const entry of entries) {
    const month = monthLabel(entry.at)
    const last = months.at(-1)
    if (last?.month === month) last.entries.push(entry)
    else months.push({ month, entries: [entry] })
  }
  return months
}

/** The answer-first line above the timeline: how many calls, and how many worked. */
export function logSummary(entries: Decision[]): string {
  if (entries.length === 0) return 'No decisions yet.'
  const worked = entries.filter((entry) => entry.experiment?.verdict === 'worked').length
  const made = `${entries.length} ${entries.length === 1 ? 'decision' : 'decisions'} so far`
  return worked === 0 ? `${made}.` : `${made}, ${worked} of which worked.`
}
