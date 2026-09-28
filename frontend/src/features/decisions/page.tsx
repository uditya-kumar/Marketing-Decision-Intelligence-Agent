import { Link } from 'react-router-dom'
import { ScrollText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/common/empty-state'
import { ErrorState } from '@/components/common/error-state'
import { PageHeader } from '@/components/common/page-header'
import { Section } from '@/components/common/section'
import { groupByMonth, logSummary } from '@/lib/decisions'
import { useDecisions } from './api'
import { DecisionEntry } from './components/decision-entry'

export default function DecisionsPage() {
  const decisions = useDecisions()

  if (decisions.isError) {
    return <ErrorState message="We couldn't load your decisions." onRetry={decisions.refetch} />
  }
  if (!decisions.data) {
    return (
      <>
        <PageHeader title="Decisions" />
        <Skeleton className="h-72" />
      </>
    )
  }

  const entries = decisions.data
  return (
    <>
      <PageHeader title="Decisions" summary={logSummary(entries)} />
      {entries.length === 0 ? (
        <EmptyState
          icon={ScrollText}
          message="Every approval, rejection and dismissal lands here with its reason and outcome."
          action={
            <Button asChild>
              <Link to="/opportunities">See opportunities</Link>
            </Button>
          }
        />
      ) : (
        groupByMonth(entries).map(({ month, entries: rows }) => (
          <Section key={month} eyebrow={month} source={`${rows.length} decided`}>
            <div className="flex flex-col rounded-lg border border-hairline bg-bone px-6">
              {rows.map((entry) => (
                <DecisionEntry key={entry.id} entry={entry} />
              ))}
            </div>
          </Section>
        ))
      )}
    </>
  )
}
