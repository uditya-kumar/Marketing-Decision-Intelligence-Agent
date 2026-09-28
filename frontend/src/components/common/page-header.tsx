import type { ReactNode } from 'react'

type PageHeaderProps = {
  title: string
  /** The answer-first summary line under the title, set in the editorial serif. */
  summary?: ReactNode
  children?: ReactNode
}

export function PageHeader({ title, summary, children }: PageHeaderProps) {
  return (
    <header className="flex flex-col gap-3">
      <h1 className="text-heading-lg font-normal text-ink">{title}</h1>
      {summary && <p className="font-serif text-[19px] leading-[1.4] text-driftwood">{summary}</p>}
      {children}
    </header>
  )
}
