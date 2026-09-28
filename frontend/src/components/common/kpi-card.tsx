import { cn } from '@/lib/utils'
import { Delta } from './delta'

type KpiCardProps = {
  label: string
  value: string
  changePct: number | null
  higherIsBetter: boolean | null
  comparison: string
  /** The goal marker line, e.g. "Target 3.5× · on track". */
  goal?: string
  /** Greys the number out when the data behind it failed a trust check. */
  muted?: boolean
  className?: string
}

export function KpiCard({
  label,
  value,
  changePct,
  higherIsBetter,
  comparison,
  goal,
  muted = false,
  className,
}: KpiCardProps) {
  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <span className="text-[13px] text-ash">{label}</span>
      <span className={`text-heading-lg ${muted ? 'text-mist' : 'text-ink'}`}>{value}</span>
      <span className="flex items-center gap-1.5 text-[13px]">
        <Delta
          changePct={changePct}
          higherIsBetter={higherIsBetter}
          className={muted ? 'text-mist' : undefined}
        />
        <span className="text-mist">{comparison}</span>
      </span>
      {goal && <span className="font-mono text-[11px] text-ash">{goal}</span>}
    </div>
  )
}
