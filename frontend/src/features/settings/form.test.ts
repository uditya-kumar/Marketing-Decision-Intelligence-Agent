import { describe, expect, it } from 'vitest'
import { toForm, toSettings } from './form'

const saved = {
  business_name: 'NovaWear',
  gross_margin_pct: 55,
  target_cpa: 500,
  target_roas: null,
  monthly_revenue_goal: 2000000,
  monthly_budgets: { google_ads: 520000 },
  festive_windows: [{ name: 'Navratri', start: '2026-10-11', end: '2026-10-20' }],
  protected_campaign_ids: [3],
}

describe('settings form', () => {
  it('round-trips saved settings', () => {
    expect(toSettings(toForm(saved))).toEqual(saved)
  })

  it('sends blank optional fields as null and drops blank budgets', () => {
    const form = { ...toForm(saved), target_cpa: ' ', monthly_budgets: { google_ads: '' } }
    const settings = toSettings(form)
    expect(settings.target_cpa).toBeNull()
    expect(settings.monthly_budgets).toEqual({})
  })

  it('starts empty before the first save', () => {
    expect(toForm(null).monthly_budgets).toEqual({ google_ads: '', meta_ads: '' })
  })
})
