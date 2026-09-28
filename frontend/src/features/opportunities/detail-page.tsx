import { ArrowLeft } from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { AiBlock } from '@/components/common/ai-block'
import { ErrorState } from '@/components/common/error-state'
import { PriorityTag } from '@/components/common/priority-dot'
import { Section } from '@/components/common/section'
import { formatShortDate } from '@/lib/format'
import { entityLine } from '@/lib/opportunities'
import { useOpportunity } from './api'
import { CauseList } from './components/cause-list'
import { DetailSkeleton } from './components/detail-skeleton'
import { DismissForm } from './components/dismiss-form'
import { EvidenceTree } from './components/evidence-tree'
import { OpportunityChart } from './components/opportunity-chart'
import { RecommendationCard } from './components/recommendation-card'
import { SignalsTable } from './components/signals-table'
import { SummaryRail } from './components/summary-rail'

function Disclosure({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <details className="group border-t border-hairline pt-4">
      <summary className="cursor-pointer list-none font-mono text-[11px] tracking-[0.6px] text-ash uppercase">
        <span className="inline-block group-open:rotate-90">▸</span> {label}
      </summary>
      <div className="pt-5">{children}</div>
    </details>
  )
}

type WhatHappenedProps = {
  observation: string
  fromLlm: boolean
  grounded: boolean
  signalCount: number
}

function WhatHappened({ observation, fromLlm, grounded, signalCount }: WhatHappenedProps) {
  const body = <p className="font-serif text-[19px] leading-[1.5] text-ink">{observation}</p>
  if (!fromLlm) {
    return (
      <Section eyebrow="What happened" source="Computed">
        {body}
      </Section>
    )
  }
  return (
    <AiBlock eyebrow="What happened" grounded={grounded} signalCount={signalCount}>
      {body}
    </AiBlock>
  )
}

export default function OpportunityDetailPage() {
  const { id } = useParams()
  const [params] = useSearchParams()
  const detail = useOpportunity(Number(id))

  if (detail.isError) {
    return <ErrorState message="We couldn't load this opportunity." onRetry={detail.refetch} />
  }
  if (!detail.data) return <DetailSkeleton />

  const { summary, tree, hypotheses, alternatives, recommendation, signals, grounded } = detail.data
  return (
    <>
      <Link
        to="/opportunities"
        className="flex items-center gap-2 text-[13px] text-ash hover:text-ink"
      >
        <ArrowLeft className="size-3.5" aria-hidden />
        All opportunities
      </Link>

      <div className="grid grid-cols-[minmax(0,732px)_300px] gap-14">
        <div className="flex flex-col gap-12">
          <header className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <PriorityTag band={summary.band} kind={summary.kind} />
              <span className="font-mono text-[11px] tracking-[0.6px] text-ash">
                {entityLine(summary)}
              </span>
              <span className="font-mono text-[11px] tracking-[0.6px] text-mist uppercase">
                detected {formatShortDate(summary.first_seen)}
              </span>
            </div>
            <h1 className="text-heading-lg font-normal text-ink">{summary.title}</h1>
          </header>

          {summary.observation && (
            <WhatHappened
              observation={summary.observation}
              // FR-8.2 lets the model write this sentence; its numbers are checked against the
              // evidence, so the label has to say which hand wrote it (UI.md §5.2).
              fromLlm={summary.diagnosis_source === 'llm'}
              grounded={grounded}
              signalCount={signals.length}
            />
          )}

          {tree && (
            <Section eyebrow="Why: evidence" source="Computed · metric decomposition">
              <EvidenceTree tree={tree} />
            </Section>
          )}

          {/* A low-priority row never goes to the investigation, so there is no hand to name. */}
          {summary.diagnosis_source === null ? (
            <Section eyebrow="Likely cause" source="Not diagnosed">
              <CauseList hypotheses={hypotheses} alternatives={alternatives} />
            </Section>
          ) : (
            <AiBlock eyebrow="Likely cause" grounded={grounded} signalCount={signals.length}>
              <CauseList hypotheses={hypotheses} alternatives={alternatives} />
            </AiBlock>
          )}

          <Section eyebrow="Recommended" source="From the action catalogue">
            {recommendation ? (
              <RecommendationCard
                recommendation={recommendation}
                actions={
                  summary.status === 'open' ? (
                    <DismissForm id={summary.id} defaultOpen={params.get('dismiss') === '1'} />
                  ) : undefined
                }
              />
            ) : (
              <div className="flex flex-col gap-5">
                <p className="text-[13px] text-ash">
                  No action was recommended for this one, so there is nothing to approve yet.
                </p>
                {summary.status === 'open' && (
                  <DismissForm id={summary.id} defaultOpen={params.get('dismiss') === '1'} />
                )}
              </div>
            )}
          </Section>

          <div className="flex flex-col gap-4">
            <Disclosure label="Charts">
              <OpportunityChart row={summary} />
            </Disclosure>
            <Disclosure label={`Raw signals (${signals.length})`}>
              <SignalsTable signals={signals} />
            </Disclosure>
          </div>
        </div>

        <SummaryRail detail={detail.data} />
      </div>
    </>
  )
}
