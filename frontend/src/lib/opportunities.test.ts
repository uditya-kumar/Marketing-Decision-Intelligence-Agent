import { describe, expect, it } from 'vitest'
import {
  ageLabel,
  attentionSummary,
  confidenceNote,
  entityLine,
  filterRows,
  impactText,
  listSummary,
  signalLabel,
  subLine,
  type Opportunity,
} from './opportunities'

function row(overrides: Partial<Opportunity> = {}): Opportunity {
  return {
    id: 1,
    key: 'meta_ads:campaign:c1:cpa',
    kind: 'issue',
    status: 'open',
    title: 'Meta "Kurta Sale" costs more per sale',
    entity_level: 'campaign',
    entity_key: 'c1',
    entity_name: 'Kurta Sale',
    channel_id: 'meta_ads',
    window: { start: '2026-10-08', end: '2026-10-14' },
    first_seen: '2026-10-14',
    primary_metric: 'cpa',
    primary_detector: 'baseline_change',
    current: 610,
    baseline: 420,
    change_pct: 45.2,
    impact: -31000,
    confidence: 0.82,
    priority: 25420,
    band: 'high',
    age_days: 3,
    signal_count: 4,
    cause: 'creative_fatigue',
    cause_label: 'Creative fatigue',
    observation: 'CPA rose 45% over 7 days.',
    diagnosis_source: 'llm',
    dismissed_reason: null,
    ...overrides,
  }
}

const issue = row()
const win = row({ id: 2, kind: 'win', impact: 8000, title: 'Google Search has room to spend' })
const dismissedWin = row({ id: 3, kind: 'win', status: 'dismissed', impact: 6000 })

describe('filterRows', () => {
  const rows = [issue, win, dismissedWin]

  it('keeps everything still on the table under "all"', () => {
    expect(filterRows(rows, 'all').map((r) => r.id)).toEqual([1, 2])
  })

  it('splits issues from wins and leaves dismissed rows out of both', () => {
    expect(filterRows(rows, 'issues').map((r) => r.id)).toEqual([1])
    expect(filterRows(rows, 'wins').map((r) => r.id)).toEqual([2])
  })

  it('shows dismissed rows only in their own segment', () => {
    expect(filterRows(rows, 'dismissed').map((r) => r.id)).toEqual([3])
  })

  it('keeps the ranked order it was given', () => {
    const reversed = [win, issue]
    expect(filterRows(reversed, 'all').map((r) => r.id)).toEqual([2, 1])
  })
})

describe('row wording', () => {
  it('signs the impact by kind', () => {
    expect(impactText(issue)).toBe('−₹31K')
    expect(impactText(win)).toBe('+₹8K')
  })

  it('says what the metric moved against, and the cause when there is one', () => {
    expect(subLine(issue)).toBe('CPA ₹610, up 45.2% on its usual level · Creative fatigue')
    expect(subLine(row({ cause_label: null, primary_detector: 'goal_breach' }))).toBe(
      'CPA ₹610, up 45.2% past your goal',
    )
  })

  it('leaves the level out of a tracking break, where it is a ratio not a count', () => {
    expect(
      subLine(
        row({
          primary_metric: 'platform_conversions',
          primary_detector: 'tracking_break',
          current: 0.2,
          change_pct: -79.8,
          cause_label: 'Broken conversion tracking',
        }),
      ),
    ).toBe('Conversions down 79.8% apart from store orders · Broken conversion tracking')
  })

  it('reads a fresh row as "Today"', () => {
    expect(ageLabel(0)).toBe('Today')
    expect(ageLabel(4)).toBe('4d')
  })

  it('names the channel and entity in the detail meta row', () => {
    expect(entityLine(issue)).toBe('META · KURTA SALE')
    expect(entityLine(row({ channel_id: null, entity_name: 'Account' }))).toBe(
      'ALL CHANNELS · ACCOUNT',
    )
  })
})

describe('confidenceNote', () => {
  it('counts the signals and flags data the analysis could not trust', () => {
    expect(confidenceNote(4, 'ok')).toBe('4 signals · data trusted')
    expect(confidenceNote(1, 'warning')).toBe('1 signal · data needs a check')
    expect(confidenceNote(2, 'broken')).toBe('2 signals · tracking is broken')
  })
})

describe('signalLabel', () => {
  it('turns a detector into a sentence', () => {
    expect(
      signalLabel({
        id: 's1',
        detector: 'tracking_break',
        metric: 'platform_conversions',
        entity: { level: 'channel', key: 'meta_ads', name: 'Meta Ads' },
        window: { start: '2026-10-08', end: '2026-10-14' },
        current: 40,
        baseline: 220,
        change_pct: -82,
        adverse: true,
        impact: -31000,
        score: 0.8,
      }),
    ).toBe('Conversions stopped matching store orders')
  })
})

describe('summaries', () => {
  it('totals what the issues cost and what the wins could add', () => {
    expect(listSummary([issue, win])).toBe(
      '1 issue is costing about ₹31K a week. 1 win could add ₹8K if you act.',
    )
  })

  it('says nothing about a kind that has no rows', () => {
    expect(listSummary([win])).toBe('1 win could add ₹8K if you act.')
    expect(listSummary([])).toBe('')
  })

  it('opens Today on the count of things needing a decision', () => {
    expect(attentionSummary([issue, win, dismissedWin])).toBe('3 things need your attention')
    expect(attentionSummary([issue])).toBe('1 thing needs your attention')
    expect(attentionSummary([])).toBe('Nothing needs you today.')
  })
})
