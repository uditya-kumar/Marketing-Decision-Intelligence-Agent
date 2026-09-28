import { describe, expect, it } from 'vitest'
import {
  reportMarkdown,
  sections,
  shortWeek,
  sourceNote,
  splitSection,
  weekRange,
  type Report,
} from './reports'

function reportRow(overrides: Partial<Report> = {}): Report {
  return {
    id: 7,
    week: { start: '2026-10-06', end: '2026-10-12' },
    summary: ['Revenue was ₹13.4L in the 7 days to 12 Oct 2026.', 'Every goal was met.'],
    detail: ["This week's KPIs. Revenue ₹13.4L, rose 6% on last week.", 'Decisions. None yet.'],
    source: 'llm',
    grounded: true,
    created_at: '2026-10-13T09:30:00',
    ...overrides,
  }
}

describe('the week a report covers', () => {
  it('spans the first and last day', () => {
    expect(shortWeek(reportRow().week)).toBe('6 Oct – 12 Oct')
    expect(weekRange(reportRow().week)).toBe('6 Oct – 12 Oct 2026')
  })
})

describe('splitSection', () => {
  it('takes the opening sentence as the heading', () => {
    expect(splitSection("This week's KPIs. Revenue ₹13.4L.")).toEqual({
      heading: "This week's KPIs",
      body: 'Revenue ₹13.4L.',
    })
  })

  it('leaves a paragraph unheaded when it opens with prose', () => {
    const prose = 'Revenue grew 6% to ₹13.4L and we stayed on budget. Search led the growth.'
    expect(splitSection(prose)).toEqual({ heading: '', body: prose })
  })

  it('leaves a single sentence unheaded', () => {
    expect(splitSection('Nothing was decided.')).toEqual({
      heading: '',
      body: 'Nothing was decided.',
    })
  })

  it('reads every detail paragraph', () => {
    expect(sections(reportRow()).map((section) => section.heading)).toEqual([
      "This week's KPIs",
      'Decisions',
    ])
  })
})

describe('sourceNote', () => {
  it('says when the AI wrote the words and they were checked', () => {
    expect(sourceNote(reportRow())).toContain('checked against them')
  })

  it('says when no AI was involved', () => {
    expect(sourceNote(reportRow({ source: 'template', grounded: false }))).toContain('no AI')
  })

  it('says when the AI draft was thrown away', () => {
    expect(sourceNote(reportRow({ grounded: false }))).toContain('failed its number check')
  })
})

describe('reportMarkdown', () => {
  const markdown = reportMarkdown(reportRow())

  it('heads the document with the week', () => {
    expect(markdown.startsWith('# Weekly report · 6 Oct – 12 Oct 2026')).toBe(true)
  })

  it('lists the founder summary as bullets', () => {
    expect(markdown).toContain('- Revenue was ₹13.4L in the 7 days to 12 Oct 2026.')
    expect(markdown).toContain('- Every goal was met.')
  })

  it('gives each detail section its own heading', () => {
    expect(markdown).toContain("## This week's KPIs\n\nRevenue ₹13.4L, rose 6% on last week.")
    expect(markdown).toContain('## Decisions\n\nNone yet.')
  })

  it('closes with how the words were written and when', () => {
    expect(markdown.trimEnd().endsWith('Generated 13 Oct, 09:30._')).toBe(true)
  })

  it('names the sections "Detail" when a paragraph has no heading', () => {
    const plain = reportMarkdown(reportRow({ detail: ['Revenue held steady.'] }))
    expect(plain).toContain('## Detail\n\nRevenue held steady.')
  })
})
