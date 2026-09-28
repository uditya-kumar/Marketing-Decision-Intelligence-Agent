// Wording and the Markdown export for the weekly report (UI.md §5.6).
// The report's sentences arrive written from the API; nothing here composes a number.
import type { Schemas } from '@/lib/api-client'
import { formatDateTime, formatShortDate, parseDate } from '@/lib/format'

export type Report = Schemas['ReportOut']
export type ReportSection = { heading: string; body: string }

// A detail paragraph opens "This week's KPIs. …"; a longer opener is prose, not a heading.
const MAX_HEADING = 40

/** "6 – 12 Oct 2026": the week a report covers. */
export function weekRange(week: Report['week']): string {
  return `${shortWeek(week)} ${parseDate(week.end).getFullYear()}`
}

/** "6 – 12 Oct", for the history rail where the year is already understood. */
export function shortWeek(week: Report['week']): string {
  return `${formatShortDate(week.start)} – ${formatShortDate(week.end)}`
}

export function generatedText(iso: string): string {
  return `Generated ${formatDateTime(iso)}`
}

/** Split a detail paragraph into its heading and the rest, for the printed sections. */
export function splitSection(paragraph: string): ReportSection {
  const at = paragraph.indexOf('. ')
  const heading = paragraph.slice(0, at)
  if (at === -1 || heading.length > MAX_HEADING) return { heading: '', body: paragraph }
  return { heading, body: paragraph.slice(at + 2) }
}

export function sections(report: Report): ReportSection[] {
  return report.detail.map(splitSection)
}

/** How the words came about, said plainly at the foot of the report (FR-11.2). */
export function sourceNote(report: Report): string {
  if (report.source === 'template') {
    return 'Written from the computed numbers alone; no AI wording was used.'
  }
  return report.grounded
    ? 'Written by AI from the computed numbers, and every number in it was checked against them.'
    : 'The AI draft failed its number check, so the computed wording was kept.'
}

/** The whole report as Markdown, for pasting into a deck or a message. */
export function reportMarkdown(report: Report): string {
  const lines = [`# Weekly report · ${weekRange(report.week)}`, '', '## For the founder', '']
  lines.push(...report.summary.map((line) => `- ${line}`))
  for (const { heading, body } of sections(report)) {
    lines.push('', `## ${heading || 'Detail'}`, '', body)
  }
  lines.push('', `_${sourceNote(report)} ${generatedText(report.created_at)}._`, '')
  return lines.join('\n')
}
