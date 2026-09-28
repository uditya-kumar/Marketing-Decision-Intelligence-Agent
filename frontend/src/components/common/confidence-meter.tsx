import { cn } from '@/lib/utils'

const STEPS = 5

type ConfidenceMeterProps = {
  /** The computed confidence, 0–1; `null` when the opportunity was never diagnosed. */
  confidence: number | null
  /** Hides the "82% confidence" text where the column is narrow; the label stays readable. */
  compact?: boolean
  className?: string
}

/** Five bars plus the percentage (UI.md §6); the number is computed, never estimated here. */
export function ConfidenceMeter({ confidence, compact = false, className }: ConfidenceMeterProps) {
  if (confidence === null) {
    return <span className={cn('font-mono text-[11px] text-mist', className)}>not diagnosed</span>
  }
  const percent = Math.round(confidence * 100)
  // A diagnosis always fills at least one bar, so low confidence still reads as a value.
  const filled = Math.max(1, Math.round(confidence * STEPS))
  return (
    <span className={cn('flex items-center gap-2', className)} title={`${percent}% confidence`}>
      <span className="flex gap-[3px]" aria-hidden>
        {Array.from({ length: STEPS }, (_, step) => (
          <span
            key={step}
            className={cn('h-1 w-2.5 rounded-[1px]', step < filled ? 'bg-ink' : 'bg-stone')}
          />
        ))}
      </span>
      <span className={cn('font-mono text-[11px] text-ash', compact && 'sr-only')}>
        {percent}% confidence
      </span>
    </span>
  )
}
