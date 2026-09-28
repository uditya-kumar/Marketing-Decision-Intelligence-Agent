import type { Schemas } from '@/lib/api-client'

type Settings = Schemas['SettingsIn']
type FestiveWindow = Schemas['FestiveWindow']

export const CHANNELS = [
  { id: 'google_ads', label: 'Google Ads' },
  { id: 'meta_ads', label: 'Meta Ads' },
] as const

/** Inputs hold text while editing; they become numbers only when the form is sent. */
export type SettingsForm = {
  business_name: string
  gross_margin_pct: string
  target_roas: string
  target_cpa: string
  monthly_revenue_goal: string
  monthly_budgets: Record<string, string>
  festive_windows: FestiveWindow[]
  protected_campaign_ids: number[]
}

function text(value: number | null | undefined): string {
  return value === null || value === undefined ? '' : String(value)
}

function optional(value: string): number | null {
  return value.trim() === '' ? null : Number(value)
}

export function toForm(settings: Settings | null): SettingsForm {
  const budgets = settings?.monthly_budgets ?? {}
  return {
    business_name: settings?.business_name ?? '',
    gross_margin_pct: text(settings?.gross_margin_pct),
    target_roas: text(settings?.target_roas),
    target_cpa: text(settings?.target_cpa),
    monthly_revenue_goal: text(settings?.monthly_revenue_goal),
    monthly_budgets: Object.fromEntries(CHANNELS.map(({ id }) => [id, text(budgets[id])])),
    festive_windows: settings?.festive_windows ?? [],
    protected_campaign_ids: settings?.protected_campaign_ids ?? [],
  }
}

export function toSettings(form: SettingsForm): Settings {
  const budgets = Object.entries(form.monthly_budgets).filter(([, value]) => value.trim() !== '')
  return {
    business_name: form.business_name.trim(),
    gross_margin_pct: Number(form.gross_margin_pct),
    target_roas: optional(form.target_roas),
    target_cpa: optional(form.target_cpa),
    monthly_revenue_goal: optional(form.monthly_revenue_goal),
    monthly_budgets: Object.fromEntries(budgets.map(([id, value]) => [id, Number(value)])),
    festive_windows: form.festive_windows,
    protected_campaign_ids: form.protected_campaign_ids,
  }
}
