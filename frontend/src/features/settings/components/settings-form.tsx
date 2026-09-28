import { useState, type ChangeEvent, type FormEvent } from 'react'
import { CircleCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ApiError, type Schemas } from '@/lib/api-client'
import { useSaveSettings } from '../api'
import { CHANNELS, toForm, toSettings, type SettingsForm as Form } from '../form'
import { FestiveWindows } from './festive-windows'
import { FieldRow } from './field-row'
import { FormSection } from './form-section'
import { ProtectedCampaigns } from './protected-campaigns'

type TextField = Exclude<
  keyof Form,
  'monthly_budgets' | 'festive_windows' | 'protected_campaign_ids'
>

type SettingsFormProps = {
  saved: Schemas['SettingsIn'] | null
  campaigns: Schemas['CampaignOut'][]
}

export function SettingsForm({ saved, campaigns }: SettingsFormProps) {
  const [form, setForm] = useState<Form>(() => toForm(saved))
  const save = useSaveSettings()
  const errors = save.error instanceof ApiError ? save.error.fieldErrors() : {}
  const formError = save.error && Object.keys(errors).length === 0 ? save.error.message : null

  function set<K extends keyof Form>(key: K, value: Form[K]) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  function text(key: TextField) {
    return {
      value: form[key],
      onChange: (e: ChangeEvent<HTMLInputElement>) => set(key, e.target.value),
      error: errors[key],
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    save.mutate(toSettings(form))
  }

  return (
    <form onSubmit={onSubmit} className="flex min-w-0 flex-1 flex-col gap-12">
      <FormSection
        title="Business & economics"
        description="Your margin decides the ROAS at which ads start making money."
      >
        <FieldRow id="business_name" label="Business name" required {...text('business_name')} />
        <FieldRow
          id="gross_margin_pct"
          label="Gross margin"
          hint="Revenue left after product costs, before ads."
          type="number"
          min={0.1}
          max={100}
          step="any"
          required
          suffix="%"
          {...text('gross_margin_pct')}
        />
      </FormSection>

      <FormSection
        title="Targets"
        description="What good looks like. Leave a target blank to skip it."
      >
        <FieldRow
          id="target_roas"
          label="Target ROAS"
          hint="Platform revenue per ₹1 of ad spend."
          type="number"
          min={0}
          step="any"
          suffix="×"
          {...text('target_roas')}
        />
        <FieldRow
          id="target_cpa"
          label="CPA limit"
          hint="The most you want to pay for one sale."
          type="number"
          min={0}
          step="any"
          prefix="₹"
          {...text('target_cpa')}
        />
        <FieldRow
          id="monthly_revenue_goal"
          label="Monthly revenue goal"
          hint="Store net sales for the month."
          type="number"
          min={0}
          step="any"
          prefix="₹"
          {...text('monthly_revenue_goal')}
        />
      </FormSection>

      <FormSection title="Monthly budgets" description="Planned ad spend per channel, for pacing.">
        {CHANNELS.map(({ id, label }) => (
          <FieldRow
            key={id}
            id={`budget_${id}`}
            label={label}
            type="number"
            min={0}
            step="any"
            prefix="₹"
            value={form.monthly_budgets[id]}
            onChange={(e) =>
              set('monthly_budgets', { ...form.monthly_budgets, [id]: e.target.value })
            }
            error={errors.monthly_budgets}
          />
        ))}
      </FormSection>

      <FormSection
        title="Festive windows"
        description="Sales and festivals where big swings are expected, so they aren't flagged."
      >
        <FestiveWindows
          windows={form.festive_windows}
          onChange={(windows) => set('festive_windows', windows)}
          error={errors.festive_windows}
        />
      </FormSection>

      <FormSection
        title="Protected campaigns"
        description="Campaigns MDIA should never recommend pausing or cutting."
      >
        <ProtectedCampaigns
          campaigns={campaigns}
          selected={form.protected_campaign_ids}
          onChange={(ids) => set('protected_campaign_ids', ids)}
          error={errors.protected_campaign_ids}
        />
      </FormSection>

      <div className="flex items-center gap-4">
        <Button type="submit" disabled={save.isPending}>
          {save.isPending ? 'Saving…' : 'Save settings'}
        </Button>
        {save.isSuccess && (
          <span className="flex items-center gap-1.5 text-[13px] text-forest">
            <CircleCheck className="size-3.5" aria-hidden />
            Saved
          </span>
        )}
        {formError && (
          <span role="alert" className="text-[13px] text-crimson">
            {formError}
          </span>
        )}
      </div>
    </form>
  )
}
