import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

type EmptyStateProps = {
  icon: LucideIcon
  message: string
  /** The single next step, usually a button or link. */
  action?: ReactNode
}

export function EmptyState({ icon: Icon, message, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-4 rounded-lg border border-hairline bg-bone px-6 py-16 text-center">
      <span className="flex size-10 items-center justify-center rounded-lg bg-linen">
        <Icon className="size-5 text-ash" aria-hidden />
      </span>
      <p className="max-w-md font-serif text-[19px] leading-[1.4] text-ink">{message}</p>
      {action}
    </div>
  )
}
