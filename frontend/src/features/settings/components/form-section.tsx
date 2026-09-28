import type { ReactNode } from 'react'

type FormSectionProps = {
  title: string
  description: string
  children: ReactNode
}

export function FormSection({ title, description, children }: FormSectionProps) {
  return (
    <section className="flex flex-col">
      <h2 className="text-heading font-normal text-ink">{title}</h2>
      <p className="pt-1 pb-3 font-serif text-[17px] leading-[1.4] text-driftwood">{description}</p>
      <div className="border-t border-hairline">{children}</div>
    </section>
  )
}
