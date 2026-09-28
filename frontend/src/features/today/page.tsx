import { Link } from 'react-router-dom'
import { Target, Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/common/empty-state'
import { ErrorState } from '@/components/common/error-state'
import { PageHeader } from '@/components/common/page-header'
import { useToday } from './api'
import { KpiStrip } from './components/kpi-strip'
import { PacingCard } from './components/pacing-card'
import { TrendChart } from './components/trend-chart'
import { TrustBanner } from './components/trust-banner'
import { greeting, trustAlert, weekSummary } from './text'

function TodaySkeleton() {
  return (
    <>
      <Skeleton className="h-24 w-2/3" />
      <div className="grid grid-cols-5 gap-6">
        {Array.from({ length: 5 }, (_, i) => (
          <Skeleton key={i} className="h-32" />
        ))}
      </div>
      <Skeleton className="h-52" />
      <div className="grid grid-cols-[minmax(0,1fr)_340px] gap-12">
        <div />
        <Skeleton className="h-64" />
      </div>
    </>
  )
}

export default function TodayPage() {
  const today = useToday()
  const title = greeting(new Date())

  if (today.isError) {
    return <ErrorState message="We couldn't load today's numbers." onRetry={today.refetch} />
  }
  if (!today.data) return <TodaySkeleton />

  const { data } = today
  if (data.as_of_date === null) {
    return (
      <>
        <PageHeader title={title} />
        {data.configured ? (
          <EmptyState
            icon={Upload}
            message="Upload your ad, analytics and store exports to see this week's numbers."
            action={
              <Button asChild>
                <Link to="/data">Upload data</Link>
              </Button>
            }
          />
        ) : (
          <EmptyState
            icon={Target}
            message="Start with your margin and goals, then upload your exports to see how the week went."
            action={
              <Button asChild>
                <Link to="/settings">Set your goals</Link>
              </Button>
            }
          />
        )}
      </>
    )
  }

  const trustIssue = trustAlert(data)
  return (
    <>
      <PageHeader title={title} summary={weekSummary(data)}>
        {!data.configured && (
          <p className="text-[13px] text-ash">
            Goals aren't set yet, so there's nothing to compare against.{' '}
            <Link to="/settings" className="text-ember hover:underline">
              Set your goals
            </Link>
          </p>
        )}
      </PageHeader>
      {trustIssue && <TrustBanner {...trustIssue} />}
      <KpiStrip kpis={data.kpis} />
      <TrendChart points={data.trend} />
      {/* The left column holds Needs attention and Opportunities from Phase 5. */}
      <div className="grid grid-cols-[minmax(0,1fr)_340px] gap-12">
        <div />
        <PacingCard pacing={data.pacing} />
      </div>
    </>
  )
}
