import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type SectionProps = {
  /** The small label above the rule, e.g. "WHAT HAPPENED". */
  eyebrow: string
  /** Where the content came from, e.g. "COMPUTED · METRIC DECOMPOSITION". */
  source?: string
  /** Sits at the right of the rule, for a marker such as the grounded chip. */
  marker?: ReactNode
  children: ReactNode
  className?: string
}

const EYEBROW = 'font-mono text-[11px] tracking-[0.6px] uppercase'

/** One labelled section of a detail page: eyebrow, its source, then the content. */
export function Section({ eyebrow, source, marker, children, className }: SectionProps) {
  return (
    <section className={cn('flex flex-col gap-4', className)}>
      <div className="flex items-center gap-2.5 border-b border-hairline pb-2.5">
        <h2 className={cn(EYEBROW, 'flex-1 font-normal text-ink')}>{eyebrow}</h2>
        {marker}
        {source && <span className={cn(EYEBROW, 'text-ash')}>{source}</span>}
      </div>
      {children}
    </section>
  )
}

/** The same eyebrow on its own, for rail headings and key/value rows. */
export function Eyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn(EYEBROW, 'text-ash', className)}>{children}</span>
}
