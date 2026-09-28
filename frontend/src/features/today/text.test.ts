import { describe, expect, it } from 'vitest'
import type { Schemas } from '@/lib/api-client'
import { goalLine, trendSummary, weekSummary } from './text'

type Kpi = Schemas['KpiSummaryOut']

const kpi = (metric: Kpi['metric'], value: number, goal: Kpi['goal'] = null): Kpi => ({
  metric,
  value,
  previous: null,
  change_pct: null,
  higher_is_better: true,
  goal,
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

describe('weekSummary', () => {
  it('leads with revenue and names the goals that are off', () => {
    const today: Schemas['TodayOut'] = {
      as_of_date: '2026-10-14',
      configured: true,
      period: { start: '2026-10-08', end: '2026-10-14' },
      kpis: [
        { ...kpi('store_revenue', 1841959.69), change_pct: -3.34 },
        kpi('cpa', 612, { target: 500, status: 'behind' }),
      ],
      trend: [],
    }
    expect(weekSummary(today)).toBe(
      'Revenue was ₹18.4L in the week to Wed, 14 Oct, down 3.3% on the week before. CPA is off goal.',
    )
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
