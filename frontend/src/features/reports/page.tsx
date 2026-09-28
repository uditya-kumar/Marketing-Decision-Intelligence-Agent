import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FileText, Loader, Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/common/empty-state'
import { ErrorState } from '@/components/common/error-state'
import { PageHeader } from '@/components/common/page-header'
import { Eyebrow } from '@/components/common/section'
import { shortWeek } from '@/lib/reports'
import { useGenerateReport, useReports } from './api'
import { ReportActions } from './components/report-actions'
import { ReportHistory } from './components/report-history'
import { ReportPaper } from './components/report-paper'

export default function ReportsPage() {
  const reports = useReports()
  const generate = useGenerateReport()
  const [weekEnd, setWeekEnd] = useState('')
  const [openId, setOpenId] = useState<number | null>(null)

  if (reports.isError) {
    return <ErrorState message="We couldn't load your reports." onRetry={reports.refetch} />
  }
  if (!reports.data) {
    return (
      <>
        <PageHeader title="Reports" />
        <Skeleton className="h-[520px]" />
      </>
    )
  }

  const rows = reports.data.reports
  const latestWeek = reports.data.next_week_end
  const week = weekEnd || latestWeek || ''
  const open = rows.find((report) => report.id === openId) ?? rows[0]

  function write() {
    generate.mutate(week || null, { onSuccess: (report) => setOpenId(report.id) })
  }

  return (
    <>
      <PageHeader
        title="Reports"
        summary={
          open
            ? `The week of ${shortWeek(open.week)}, written from this week's computed numbers.`
            : 'One week of numbers, decisions and outcomes, written for the founder.'
        }
      />

      <div className="flex flex-wrap items-end justify-between gap-4 print:hidden">
        <label className="flex flex-col gap-1.5">
          <Eyebrow>Week ending</Eyebrow>
          <Input
            type="date"
            value={week}
            max={latestWeek ?? undefined}
            disabled={latestWeek === null}
            onChange={(event) => setWeekEnd(event.target.value)}
            className="w-44"
          />
        </label>
        <Button onClick={write} disabled={generate.isPending || latestWeek === null}>
          {generate.isPending ? <Loader className="animate-spin" aria-hidden /> : null}
          {generate.isPending ? 'Writing' : 'Generate'}
        </Button>
      </div>

      {generate.isError && (
        <ErrorState message="We couldn't write that week's report." onRetry={write} />
      )}

      {latestWeek === null ? (
        <EmptyState
          icon={Upload}
          message="Upload your ad, analytics and store exports, then a week can be reported on."
          action={
            <Button asChild>
              <Link to="/data">Upload data</Link>
            </Button>
          }
        />
      ) : open === undefined ? (
        <EmptyState
          icon={FileText}
          message="No report yet. Generate one and this week's numbers, decisions and outcomes are written up in a page."
        />
      ) : (
        <div className="grid grid-cols-[200px_minmax(0,1fr)] gap-12 print:block">
          <ReportHistory reports={rows} selectedId={open.id} onSelect={setOpenId} />
          <div className="flex flex-col gap-4">
            <div className="flex justify-end">
              <ReportActions report={open} />
            </div>
            <ReportPaper report={open} />
          </div>
        </div>
      )}
    </>
  )
}
