import type { ComponentProps, ReactNode } from 'react'
import { Input } from '@/components/ui/input'

export const INPUT_CLASS = 'h-auto rounded-lg border-stone bg-bone px-3 py-[9px] text-body-sm'

type FieldRowProps = {
  id: string
  label: string
  hint?: string
  error?: string
  /** A unit shown before (₹) or after (%, ×) the input. */
  prefix?: string
  suffix?: string
  children?: ReactNode
} & Omit<ComponentProps<'input'>, 'id' | 'prefix' | 'children'>

/** Label and hint on the left, the input on the right, per the Settings layout. */
export function FieldRow({
  id,
  label,
  hint,
  error,
  prefix,
  suffix,
  children,
  ...input
}: FieldRowProps) {
  return (
    <div className="flex items-start justify-between gap-8 border-b border-hairline py-[18px]">
      <label htmlFor={id} className="flex flex-col gap-0.5">
        <span className="text-ink">{label}</span>
        {hint && <span className="text-[13px] text-ash">{hint}</span>}
      </label>
      <div className="flex flex-col items-end gap-1">
        {children ?? (
          <span className="flex items-center gap-2">
            {prefix && <span className="text-ash">{prefix}</span>}
            <Input
              id={id}
              aria-invalid={error ? true : undefined}
              className={`${INPUT_CLASS} w-[180px]`}
              {...input}
            />
            <span className="w-3 text-ash">{suffix}</span>
          </span>
        )}
        {error && <span className="text-[13px] text-crimson">{error}</span>}
      </div>
    </div>
  )
}
