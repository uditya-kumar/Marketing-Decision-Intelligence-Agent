import type { Schemas } from '@/lib/api-client'
import { cn } from '@/lib/utils'

type Band = Schemas['OpportunityOut']['band']
type Kind = Schemas['OpportunityOut']['kind']

const BANDS: Record<Band, { label: string; colour: string }> = {
  high: { label: 'High', colour: 'bg-crimson' },
  medium: { label: 'Medium', colour: 'bg-amber' },
  low: { label: 'Low', colour: 'bg-mist' },
}
// A win is never alarming, however big it is, so its dot stays positive.
const WIN = { colour: 'bg-verdant', text: 'text-verdant' }
const BAND_TEXT: Record<Band, string> = {
  high: 'text-crimson',
  medium: 'text-amber',
  low: 'text-mist',
}

function tone(band: Band, kind: Kind) {
  return {
    label: `${BANDS[band].label} priority ${kind}`,
    colour: kind === 'win' ? WIN.colour : BANDS[band].colour,
    text: kind === 'win' ? WIN.text : BAND_TEXT[band],
  }
}

type PriorityProps = { band: Band; kind: Kind }

/** The list-row dot; the priority it stands for is in its label, never colour alone. */
export function PriorityDot({ band, kind }: PriorityProps) {
  const { label, colour } = tone(band, kind)
  return (
    <span className={cn('size-2 shrink-0 rounded-full', colour)} role="img" aria-label={label} />
  )
}

/** The same priority as a dot with its word, for the opportunity page header. */
export function PriorityTag({ band, kind }: PriorityProps) {
  const { label, colour, text } = tone(band, kind)
  return (
    <span className="flex items-center gap-1.5" title={label}>
      <span className={cn('size-1.5 shrink-0 rounded-full', colour)} aria-hidden />
      <span className={cn('font-mono text-[11px] tracking-[0.6px] uppercase', text)}>
        {BANDS[band].label}
      </span>
    </span>
  )
}
