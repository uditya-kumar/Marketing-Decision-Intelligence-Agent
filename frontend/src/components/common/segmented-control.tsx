import { cn } from '@/lib/utils'

type SegmentedControlProps<T extends string> = {
  label: string
  /** `count` is shown next to the label where the segment filters a list. */
  options: { value: T; label: string; count?: number }[]
  value: T
  onChange: (value: T) => void
}

export function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
}: SegmentedControlProps<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="flex rounded-lg border border-hairline bg-bone p-0.5"
    >
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={option.value === value}
          onClick={() => onChange(option.value)}
          className={cn(
            'flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[12px] transition-colors duration-150 ease-out',
            option.value === value
              ? 'border-hairline bg-parchment text-ink'
              : 'border-transparent text-ash hover:text-ink',
          )}
        >
          {option.label}
          {option.count !== undefined && (
            <span className="font-mono text-[11px] text-ash">{option.count}</span>
          )}
        </button>
      ))}
    </div>
  )
}
