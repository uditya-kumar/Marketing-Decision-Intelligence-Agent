import { CircleCheck, CircleDashed, CircleX, Hourglass, TriangleAlert } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { TrustSummary, TrustTone } from '@/lib/trust'
import { cn } from '@/lib/utils'

const TONES: Record<TrustTone, { icon: LucideIcon; className: string }> = {
  ok: { icon: CircleCheck, className: 'text-forest' },
  stale: { icon: Hourglass, className: 'text-amber' },
  warning: { icon: TriangleAlert, className: 'text-amber' },
  broken: { icon: CircleX, className: 'text-crimson' },
  empty: { icon: CircleDashed, className: 'text-ash' },
}

/** A source's trust status (ok / warning / broken), with an optional one-line reason. */
export function TrustBadge({ tone, label, note }: TrustSummary) {
  const { icon: Icon, className } = TONES[tone]
  return (
    <span className="flex flex-col gap-0.5">
      <span className={cn('flex items-center gap-1.5 text-[13px]', className)}>
        <Icon className="size-3.5 shrink-0" aria-hidden />
        {label}
      </span>
      {note && <span className="text-[12px] text-ash">{note}</span>}
    </span>
  )
}
