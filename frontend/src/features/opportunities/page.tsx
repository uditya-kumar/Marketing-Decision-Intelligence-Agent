import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CircleCheck, Info, Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/common/empty-state'
import { ErrorState } from '@/components/common/error-state'
import { PageHeader } from '@/components/common/page-header'
import { SegmentedControl } from '@/components/common/segmented-control'
import { filterRows, listSummary, type OpportunityFilter } from '@/lib/opportunities'
import { useOpportunities } from './api'
import { OpportunityTable } from './components/opportunity-table'

const LABELS: Record<OpportunityFilter, string> = {
  all: 'All',
  issues: 'Issues',
  wins: 'Wins',
  dismissed: 'Dismissed',
}

const EMPTY: Record<OpportunityFilter, string> = {
  all: 'All clear. The last analysis found nothing worth your time.',
  issues: 'No issues right now. Every channel is inside its goals.',
  wins: 'No wins to chase yet. They show up when a channel beats its goal with room to spend.',
  dismissed: 'Nothing has been dismissed. Rows you set aside with a reason appear here.',
}

function TableSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: 5 }, (_, row) => (
        <Skeleton key={row} className="h-[73px]" />
      ))}
    </div>
  )
}

export default function OpportunitiesPage() {
  const opportunities = useOpportunities()
  const [filter, setFilter] = useState<OpportunityFilter>('all')

  if (opportunities.isError) {
    return (
      <ErrorState message="We couldn't load your opportunities." onRetry={opportunities.refetch} />
    )
  }

  const rows = opportunities.data
  const options = (Object.keys(LABELS) as OpportunityFilter[]).map((value) => ({
    value,
    label: LABELS[value],
    count: rows && filterRows(rows, value).length,
  }))
  const shown = rows ? filterRows(rows, filter) : []

  return (
    <>
      <PageHeader title="Opportunities" summary={rows && listSummary(filterRows(rows, 'all'))} />
      {rows?.length === 0 ? (
        <EmptyState
          icon={Upload}
          message="Upload this week's exports and the analysis will list what needs a decision."
          action={
            <Button asChild>
              <Link to="/data">Upload data</Link>
            </Button>
          }
        />
      ) : (
        <>
          <SegmentedControl
            label="Filter opportunities"
            options={options}
            value={filter}
            onChange={setFilter}
          />
          {!rows ? (
            <TableSkeleton />
          ) : shown.length === 0 ? (
            <EmptyState icon={CircleCheck} message={EMPTY[filter]} />
          ) : (
            <OpportunityTable rows={shown} />
          )}
          <p className="flex items-center gap-2 text-[13px] text-ash">
            <Info className="size-3.5 shrink-0" aria-hidden />
            Priority is the rupees at stake in a week times how confident the evidence is. The dot
            shows which band that lands in.
          </p>
        </>
      )}
    </>
  )
}
