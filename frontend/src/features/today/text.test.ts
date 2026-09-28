import { describe, expect, it } from 'vitest'
import type { Schemas } from '@/lib/api-client'
import {
  budgetLine,
  goalLine,
  paceLine,
  suggestionLine,
  trendSummary,
  trustAlert,
  weekSummary,
} from './text'

type Kpi = Schemas['KpiSummaryOut']
type SourceTrust = Schemas['SourceTrustOut']
type Today = Schemas['TodayOut']

const kpi = (metric: Kpi['metric'], value: number, goal: Kpi['goal'] = null): Kpi => ({
  metric,
  value,
  previous: null,
  change_pct: null,
  higher_is_better: true,
  goal,
  reliable: true,
})

describe('goalLine', () => {
  it('phrases each goal for its metric', () => {
    expect(goalLine(kpi('roas', 3.9, { target: 3.5, status: 'ahead' }))).toBe('Target 3.5× · ahead')
    expect(goalLine(kpi('cpa', 428, { target: 500, status: 'ahead' }))).toBe(
      'Limit ₹500 · well within',
    )
    expect(goalLine(kpi('mer', 5, { target: 100 / 55, status: 'ahead' }))).toBe(
      'Break-even 1.8× · above',
    )
    expect(goalLine(kpi('store_revenue', 3e5, { target: 350000, status: 'on_track' }))).toBe(
      'Goal ₹3.5L · on track',
    )
    expect(goalLine(kpi('spend', 1000))).toBeUndefined()
  })
})

const fresh = (source: SourceTrust['source']): SourceTrust => ({
  source,
  label: source === 'meta_ads' ? 'Meta Ads' : 'Store orders (Shopify)',
  status: 'ok',
  freshness: { last_date: '2026-10-28', days_behind: 0, missing_dates: [] },
  tracking: null,
})

const brokenMeta: SourceTrust = {
  ...fresh('meta_ads'),
  status: 'broken',
  tracking: {
    status: 'broken',
    ratio_change: 0.16,
    since: '2026-10-24',
    conversions_change_pct: -82.4,
    orders_change_pct: 2.1,
  },
}

function todayWith(overrides: Partial<Today> = {}): Today {
  return {
    as_of_date: '2026-10-14',
    configured: true,
    period: { start: '2026-10-08', end: '2026-10-14' },
    kpis: [],
    trend: [],
    trust: { as_of_date: '2026-10-14', sources: [fresh('meta_ads'), fresh('store_orders')] },
    pacing: { month: null, total: null, channels: [] },
    attention: [],
    wins: [],
    analysing: false,
    ...overrides,
  }
}

describe('trustAlert', () => {
  it('stays quiet when every source is fine', () => {
    expect(trustAlert(todayWith())).toBeUndefined()
  })

  it('warns not to touch campaigns while tracking is broken', () => {
    const today = todayWith({
      kpis: [
        { ...kpi('roas', 1.2), reliable: false },
        { ...kpi('cpa', 900), reliable: false },
      ],
      trust: { as_of_date: '2026-10-28', sources: [brokenMeta, fresh('store_orders')] },
    })
    expect(trustAlert(today)).toEqual({
      title: 'Meta tracking looks broken since 24 Oct',
      body:
        'Meta reports purchases down 82.4% while store orders are normal. ' +
        "Don't change Meta campaigns until tracking is fixed. ROAS and CPA are greyed out meanwhile.",
    })
  })

  it('puts a broken source ahead of a stale one and counts the rest', () => {
    const stale: SourceTrust = {
      ...fresh('store_orders'),
      status: 'warning',
      freshness: { last_date: '2026-10-25', days_behind: 3, missing_dates: [] },
    }
    const today = todayWith({ trust: { as_of_date: '2026-10-25', sources: [stale, brokenMeta] } })
    const alert = trustAlert(today)
    expect(alert?.title).toBe('Meta tracking looks broken since 24 Oct')
    expect(alert?.body).toMatch(/1 other source needs a look too\.$/)

    const onlyStale = todayWith({ trust: { as_of_date: '2026-10-25', sources: [stale] } })
    expect(trustAlert(onlyStale)).toEqual({
      title: 'Store orders (Shopify) is 3 days behind',
      body:
        'Upload the latest Store orders (Shopify) export to catch up. ' +
        'Numbers stop at Wed, 14 Oct, the last day every source covers.',
    })
  })

  it('lists missing days', () => {
    const gappy: SourceTrust = {
      ...fresh('store_orders'),
      status: 'warning',
      freshness: { last_date: '2026-10-28', days_behind: 0, missing_dates: ['2026-10-03'] },
    }
    const today = todayWith({ trust: { as_of_date: '2026-10-28', sources: [gappy] } })
    expect(trustAlert(today)?.title).toBe('Store orders (Shopify) is missing 1 day')
  })
})

describe('pacing lines', () => {
  const pacing: Schemas['PacingOut'] = {
    budget: 800000,
    spent: 442606,
    spent_pct: 55.33,
    remaining_budget: 357394,
    month_elapsed_pct: 45.16,
    projected: 980056,
    status: 'over',
    daily_run_rate: 31614.7,
    suggested_daily: 21610.2,
  }

  it('shows how far spend has gone past the budget', () => {
    const overspent = {
      ...pacing,
      budget: 1420000,
      spent: 1444835.74,
      spent_pct: 101.75,
      remaining_budget: -24835.74,
    }
    expect(budgetLine(overspent)).toBe('₹14.4L of ₹14.2L · ₹24.8K over')
  })

  it('says how the month is pacing and what to spend instead', () => {
    expect(paceLine(pacing)).toBe('Over pace · 45.2% of month gone')
    expect(budgetLine(pacing)).toBe('₹4.4L of ₹8L · ₹3.6L left')
    expect(suggestionLine(pacing)).toBe('Suggested ₹21.6K/day to land on plan · now ₹31.6K/day')
    expect(suggestionLine({ ...pacing, suggested_daily: null })).toBeUndefined()
    expect(suggestionLine({ ...pacing, suggested_daily: 0 })).toBe(
      'Budget used up · now ₹31.6K/day',
    )
  })
})

describe('weekSummary', () => {
  it('leads with revenue and names the goals that are off', () => {
    const today = todayWith({
      kpis: [
        { ...kpi('store_revenue', 1841959.69), change_pct: -3.34 },
        kpi('cpa', 612, { target: 500, status: 'behind' }),
      ],
    })
    expect(weekSummary(today)).toBe(
      'Revenue was ₹18.4L in the week to Wed, 14 Oct, down 3.3% on the week before. CPA is off goal.',
    )
  })

  it('lists several missed goals but skips ones tracking has made unreliable', () => {
    const today = todayWith({
      kpis: [
        kpi('store_revenue', 1640000, { target: 1810000, status: 'behind' }),
        kpi('mer', 1.5, { target: 1.8, status: 'behind' }),
        { ...kpi('roas', 3.2, { target: 3.5, status: 'behind' }), reliable: false },
        kpi('cpa', 612, { target: 500, status: 'behind' }),
      ],
    })
    expect(weekSummary(today)).toContain('Revenue, MER and CPA are off goal.')
  })
})

describe('trendSummary', () => {
  it('names the highest and lowest days and skips gaps', () => {
    const point = (date: string, spend: number | null) => ({
      date,
      spend,
      store_revenue: null,
      roas: null,
      mer: null,
      cpa: null,
    })
    const points = [point('2026-10-01', 900), point('2026-10-02', null), point('2026-10-03', 1500)]
    expect(trendSummary(points, 'spend')).toBe(
      'Highest on 3 Oct (₹1,500), lowest on 1 Oct (₹900). Dark bars are the last 7 days.',
    )
    expect(trendSummary(points, 'cpa')).toBe('No CPA recorded in the last 30 days.')
  })
})
