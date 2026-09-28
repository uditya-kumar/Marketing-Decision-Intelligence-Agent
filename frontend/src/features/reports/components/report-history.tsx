import { Eyebrow } from '@/components/common/section'
import { shortWeek, type Report } from '@/lib/reports'
import { formatShortDate } from '@/lib/format'
import { cn } from '@/lib/utils'

type ReportHistoryProps = {
  reports: Report[]
  selectedId: number
  onSelect: (id: number) => void
}

/** The list of past reports; picking one opens it in the document view. */
export function ReportHistory({ reports, selectedId, onSelect }: ReportHistoryProps) {
  return (
    <nav className="flex flex-col gap-2 print:hidden" aria-label="Past reports">
      <Eyebrow className="pb-1">Past reports</Eyebrow>
      {reports.map((report) => (
        <button
          key={report.id}
          type="button"
          onClick={() => onSelect(report.id)}
          aria-current={report.id === selectedId}
          className={cn(
            'flex flex-col items-start gap-0.5 rounded-lg px-3 py-2 text-left transition-colors duration-150 ease-out',
            report.id === selectedId ? 'bg-linen' : 'hover:bg-linen/60',
          )}
        >
          <span className="text-ink">{shortWeek(report.week)}</span>
          <span className="font-mono text-[11px] tracking-[0.6px] text-ash">
            written {formatShortDate(report.created_at)}
            {report.source === 'template' && ' · rule-based'}
          </span>
        </button>
      ))}
    </nav>
  )
}
