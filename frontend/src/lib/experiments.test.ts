import { describe, expect, it } from 'vitest'
import {
  awaitingLine,
  experimentsSummary,
  filterExperiments,
  firstFilledTab,
  movementText,
  outcomeLine,
  progressPct,
  progressText,
  todayLine,
  verdictChip,
  watchLine,
} from './experiments'
import { experimentRow } from './test-rows'

const draft = experimentRow()
const running = experimentRow({
  id: 11,
  status: 'running',
  started_on: '2026-10-15',
  ends_on: '2026-10-21',
  progress: { day: 4, total: 7, due: false },
})
const worked = experimentRow({
  id: 12,
  status: 'completed',
  verdict: 'worked',
  before: 610,
  after: 420,
  sample_days: 7,
  evaluated_on: '2026-10-22',
})
const rejected = experimentRow({ id: 13, status: 'rejected', reason: 'Sale week, not the ad.' })

describe('filterExperiments', () => {
  const rows = [draft, running, worked, rejected]

  it('puts each status under the tab that decides it', () => {
    expect(filterExperiments(rows, 'awaiting').map((r) => r.id)).toEqual([10])
    expect(filterExperiments(rows, 'running').map((r) => r.id)).toEqual([11])
  })

  it('files a rejected change with the finished ones: decided, just not tried', () => {
    expect(filterExperiments(rows, 'completed').map((r) => r.id)).toEqual([12, 13])
  })
})

describe('firstFilledTab', () => {
  it('opens on what needs a decision when anything does', () => {
    expect(firstFilledTab([worked, draft])).toBe('awaiting')
  })

  it('otherwise opens on a tab that has something to show', () => {
    expect(firstFilledTab([worked])).toBe('completed')
    expect(firstFilledTab([running])).toBe('running')
    expect(firstFilledTab([])).toBe('awaiting')
  })
})

describe('progress', () => {
  it('reads the day out of the duration', () => {
    expect(progressText({ day: 4, total: 7, due: false })).toBe('Day 4 of 7')
  })

  it('fills the bar by day and never past the end', () => {
    expect(progressPct({ day: 0, total: 7, due: false })).toBe(0)
    expect(progressPct({ day: 9, total: 7, due: true })).toBe(100)
    expect(progressPct({ day: 0, total: 0, due: false })).toBe(0)
  })
})

describe('movementText', () => {
  it('shows where a finished change went, and where an unstarted one should go', () => {
    expect(movementText(worked)).toBe('₹610 → ₹420')
    expect(movementText(draft)).toBe('₹610 → ₹420')
  })

  it('has nothing to show when neither reading exists', () => {
    expect(movementText(experimentRow({ baseline: null, target: null }))).toBe('—')
  })
})

describe('watchLine', () => {
  it('names the window once the change is under way', () => {
    expect(watchLine(running)).toBe('Watching CPA · 15 Oct to 21 Oct')
  })

  it('says how long it will run while it is still waiting', () => {
    expect(watchLine(draft)).toBe('Watching CPA for 7 days once you approve it')
  })
})

describe('outcomeLine', () => {
  it('gives the two readings and how much data judged them', () => {
    expect(outcomeLine(worked)).toBe('CPA ₹610 → ₹420 over 7 days.')
  })

  it('keeps the reason a rejection was given', () => {
    expect(outcomeLine(rejected)).toBe('Sale week, not the ad.')
    expect(outcomeLine(experimentRow({ status: 'rejected' }))).toBe(
      'Turned down, so nothing changed.',
    )
  })

  it('waits for the data rather than guessing an outcome', () => {
    expect(outcomeLine(experimentRow({ status: 'completed' }))).toBe(
      'Waiting for the week of data that judges it.',
    )
  })
})

describe('verdictChip', () => {
  it('colours the three verdicts', () => {
    expect(verdictChip('worked')).toEqual({ label: 'Worked', className: 'text-verdant' })
    expect(verdictChip('did_not_work').label).toBe("Didn't work")
    expect(verdictChip('inconclusive').className).toBe('text-ash')
  })
})

describe('the Today strip', () => {
  it('names the action and how far it has got', () => {
    expect(todayLine(running)).toBe('Creative rotation · Day 4 of 7')
    expect(todayLine(worked)).toBe('Creative rotation completed')
    expect(todayLine(draft)).toBe('Creative rotation')
  })

  it('counts what is waiting on a decision', () => {
    expect(awaitingLine(1)).toBe('1 awaiting approval')
  })
})

describe('experimentsSummary', () => {
  it('leads with what needs a decision, then what is being measured', () => {
    expect(experimentsSummary([draft, running, worked])).toBe(
      '1 change is waiting on you. 1 change is being measured. 1 change worked.',
    )
  })

  it('pluralises and skips what there is none of', () => {
    expect(experimentsSummary([running, running])).toBe('2 changes are being measured.')
    expect(experimentsSummary([])).toBe('Nothing is under test yet.')
  })
})
