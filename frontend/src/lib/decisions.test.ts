import { describe, expect, it } from 'vitest'
import { decisionLabel, decisionLine, groupByMonth, logSummary, monthLabel } from './decisions'
import { decisionRow, experimentRow } from './test-rows'

const approved = decisionRow()
const rejected = decisionRow({
  id: 101,
  kind: 'reject',
  reason: 'Sale week, not the ad.',
  experiment: experimentRow({ status: 'rejected' }),
})
const dismissed = decisionRow({
  id: 102,
  kind: 'dismiss',
  reason: 'Expected, we cut the budget.',
  experiment: null,
  at: '2026-09-28T11:00:00',
})

describe('decisionLine', () => {
  it('names the action that was approved or turned down', () => {
    expect(decisionLine(approved)).toBe('Approved: creative rotation')
    expect(decisionLine(rejected)).toBe('Rejected: creative rotation')
  })

  it('falls back to the opportunity when nothing was tried', () => {
    expect(decisionLine(dismissed)).toBe('Dismissed: Meta "Kurta Sale" costs more per sale')
  })

  it('labels the three kinds', () => {
    expect(decisionLabel('approve')).toBe('Approved')
    expect(decisionLabel('reject')).toBe('Rejected')
    expect(decisionLabel('dismiss')).toBe('Dismissed')
  })
})

describe('groupByMonth', () => {
  it('heads each group with its month', () => {
    expect(monthLabel('2026-10-14T09:30:00')).toBe('October 2026')
  })

  it('keeps the order the API sent and starts a group when the month changes', () => {
    expect(groupByMonth([approved, rejected, dismissed])).toEqual([
      { month: 'October 2026', entries: [approved, rejected] },
      { month: 'September 2026', entries: [dismissed] },
    ])
  })

  it('has no groups when nothing has been decided', () => {
    expect(groupByMonth([])).toEqual([])
  })
})

describe('logSummary', () => {
  it('counts the calls made and the ones that paid off', () => {
    const worked = decisionRow({ experiment: experimentRow({ verdict: 'worked' }) })
    expect(logSummary([approved, rejected])).toBe('2 decisions so far.')
    expect(logSummary([worked])).toBe('1 decision so far, 1 of which worked.')
    expect(logSummary([])).toBe('No decisions yet.')
  })
})
