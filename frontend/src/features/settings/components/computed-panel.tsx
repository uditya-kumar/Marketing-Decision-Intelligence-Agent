import { CircleCheck, TriangleAlert } from 'lucide-react'
import type { Schemas } from '@/lib/api-client'
import { formatRatio } from '@/lib/format'

const LABEL = 'font-mono text-[11px] tracking-[0.6px] text-ash uppercase'

function RoasCheck({
  target,
  breakEven,
  profitable,
}: {
  target: number
  breakEven: number
  profitable: boolean
}) {
  const Icon = profitable ? CircleCheck : TriangleAlert
  const comparison = `Your target ROAS (${formatRatio(target)}) is ${profitable ? 'above' : 'at or below'} break-even (${formatRatio(breakEven)})`
  return (
    <p className="flex gap-2 border-t border-hairline pt-4 text-[13px] text-ink">
      <Icon
        className={`mt-0.5 size-3.5 shrink-0 ${profitable ? 'text-forest' : 'text-amber'}`}
        aria-hidden
      />
      {profitable
        ? `${comparison}, so hitting it is profitable.`
        : `${comparison}, so hitting it still loses money.`}
    </p>
  )
}

/** Values the server derives from the saved settings; they refresh on save. */
export function ComputedPanel({ view }: { view: Schemas['SettingsOut'] }) {
  const breakEven = view.break_even_roas
  const target = view.settings?.target_roas ?? null
  return (
    <aside className="sticky top-8 flex w-[300px] shrink-0 flex-col gap-5 self-start rounded-lg border border-hairline bg-bone p-6">
      <span className={LABEL}>Calculated for you</span>
      <div className="flex flex-col gap-1">
        <span className={LABEL}>Break-even ROAS</span>
        <span className="text-heading text-ink">
          {breakEven === null ? '—' : formatRatio(breakEven)}
        </span>
        <span className="text-[13px] text-ash">
          {breakEven === null
            ? 'Save your gross margin to see it.'
            : 'Below this, ads lose money after product costs.'}
        </span>
      </div>
      {breakEven !== null && target !== null && view.target_roas_profitable !== null && (
        <RoasCheck target={target} breakEven={breakEven} profitable={view.target_roas_profitable} />
      )}
    </aside>
  )
}
