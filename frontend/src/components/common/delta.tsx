import { cn } from '@/lib/utils'
import { formatPercent } from '@/lib/format'

type DeltaProps = {
  changePct: number | null
  /** From the API: `null` means the direction is neither good nor bad (e.g. spend). */
  higherIsBetter: boolean | null
  className?: string
}

/** ▲▼ + %, coloured by whether the change is good for the business, not by its direction. */
export function Delta({ changePct, higherIsBetter, className }: DeltaProps) {
  if (changePct === null) {
    return <span className={cn('text-ash', className)}>—</span>
  }
  const flat = Math.abs(changePct) < 0.05
  const good = higherIsBetter === null || flat ? null : changePct > 0 === higherIsBetter
  return (
    <span
      className={cn(
        good === null && 'text-ash',
        good === true && 'text-verdant',
        good === false && 'text-crimson',
        className,
      )}
    >
      {flat ? '■' : changePct > 0 ? '▲' : '▼'} {formatPercent(Math.abs(changePct))}
    </span>
  )
}
