import { describe, expect, it } from 'vitest'
import type { Schemas } from '@/lib/api-client'
import { signedPercent, trustSummary } from './trust'

type SourceTrust = Schemas['SourceTrustOut']

const source = (overrides: Partial<SourceTrust> = {}): SourceTrust => ({
  source: 'meta_ads',
  label: 'Meta Ads',
  status: 'ok',
  freshness: { last_date: '2026-10-28', days_behind: 0, missing_dates: [] },
  tracking: null,
  ...overrides,
})

describe('trustSummary', () => {
  it('reads OK for a fresh source', () => {
    expect(trustSummary(source())).toEqual({ tone: 'ok', label: 'OK' })
  })

  it('names the tracking break and when it started', () => {
    const tracking = {
      status: 'broken' as const,
      ratio_change: 0.16,
      since: '2026-10-24',
      conversions_change_pct: -82.4,
      orders_change_pct: 2.1,
    }
    expect(trustSummary(source({ status: 'broken', tracking }))).toEqual({
      tone: 'broken',
      label: 'Broken',
      note: 'Purchases −82.4% vs store orders since 24 Oct',
    })
  })

  it('flags stale sources, gaps and missing data', () => {
    const behind = { last_date: '2026-10-21', days_behind: 7, missing_dates: [] }
    expect(trustSummary(source({ freshness: behind }))).toEqual({
      tone: 'stale',
      label: 'Stale',
      note: '7 days behind',
    })
    const gaps = { last_date: '2026-10-28', days_behind: 0, missing_dates: ['2026-10-03'] }
    expect(trustSummary(source({ freshness: gaps })).note).toBe('1 day missing')
    const none = { last_date: null, days_behind: 0, missing_dates: [] }
    expect(trustSummary(source({ freshness: none }))).toEqual({
      tone: 'empty',
      label: 'No data yet',
    })
  })
})

describe('signedPercent', () => {
  it('always shows the sign', () => {
    expect(signedPercent(3)).toBe('+3%')
    expect(signedPercent(-82.44)).toBe('−82.4%')
    expect(signedPercent(0)).toBe('0%')
  })
})
