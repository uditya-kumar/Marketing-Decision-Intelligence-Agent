import { Ruler, ShieldCheck } from 'lucide-react'
import type { ReactNode } from 'react'
import { Section } from './section'

type AiBlockProps = {
  eyebrow: string
  /** True when the LLM's words passed the grounding guard; false means the rules wrote them. */
  grounded: boolean
  /** How many signals the words were checked against, shown on the chip. */
  signalCount: number
  children: ReactNode
}

function GroundedChip({ grounded, signalCount }: Omit<AiBlockProps, 'eyebrow' | 'children'>) {
  const Icon = grounded ? ShieldCheck : Ruler
  return (
    <span className="flex items-center gap-1.5 rounded-sm bg-linen px-2 py-[3px] text-[12px] text-ink">
      <Icon className={`size-3 ${grounded ? 'text-verdant' : 'text-ash'}`} aria-hidden />
      {grounded
        ? `AI · grounded in ${signalCount} ${signalCount === 1 ? 'signal' : 'signals'}`
        : 'Rule-based · no AI answer used'}
    </span>
  )
}

/** A section whose words came from the LLM, labelled so it never reads as a computed fact. */
export function AiBlock({ eyebrow, grounded, signalCount, children }: AiBlockProps) {
  return (
    <Section
      eyebrow={eyebrow}
      marker={<GroundedChip grounded={grounded} signalCount={signalCount} />}
    >
      {children}
    </Section>
  )
}
