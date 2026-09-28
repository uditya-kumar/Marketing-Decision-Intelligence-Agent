import { ShieldCheck, Ruler } from 'lucide-react'
import { Eyebrow } from '@/components/common/section'
import { formatDateTime } from '@/lib/format'
import { sections, sourceNote, weekRange, type Report } from '@/lib/reports'

/** One numbered line of a detail section, the way the printed report sets them. */
function Line({ index, text }: { index: number; text: string }) {
  return (
    <li className="flex gap-3">
      <span className="w-4 shrink-0 pt-[3px] font-mono text-[11px] tracking-[0.6px] text-mist">
        {String(index + 1).padStart(2, '0')}
      </span>
      <span className="flex-1 text-ink">{text}</span>
    </li>
  )
}

/** A detail paragraph as a headed section; its sentences are listed one per line. */
function DetailSection({ heading, body }: { heading: string; body: string }) {
  const lines = body.split(/(?<=\.)\s+/).filter(Boolean)
  return (
    <section className="flex flex-col gap-3">
      {heading && <h3 className="text-heading-sm font-normal text-ink">{heading}</h3>}
      <ol className="flex flex-col gap-2">
        {lines.map((line, index) => (
          <Line key={line} index={index} text={line} />
        ))}
      </ol>
    </section>
  )
}

/** The report as a document: the founder summary on top, the team detail below (UI.md §5.6). */
export function ReportPaper({ report }: { report: Report }) {
  const [headline, ...rest] = report.summary
  const Icon = report.grounded ? ShieldCheck : Ruler
  return (
    <article className="flex flex-col gap-8 rounded-lg border border-hairline bg-bone px-16 py-14 print:gap-6 print:border-0 print:bg-transparent print:px-0 print:py-0">
      <header className="flex flex-col gap-3">
        <Eyebrow>Weekly report · for the founder</Eyebrow>
        <h2 className="font-serif text-[30px] leading-[1.2] text-ink">{headline}</h2>
        <p className="font-mono text-[12px] text-ash">
          {weekRange(report.week)} · generated {formatDateTime(report.created_at)}
        </p>
      </header>

      {rest.length > 0 && (
        <p className="font-serif text-[19px] leading-[1.5] text-driftwood">{rest.join(' ')}</p>
      )}

      <div className="flex flex-col gap-8 border-t border-hairline pt-8">
        {sections(report).map(({ heading, body }) => (
          <DetailSection key={heading || body} heading={heading} body={body} />
        ))}
      </div>

      <footer className="flex items-center gap-2 border-t border-hairline pt-5">
        <Icon
          className={`size-3.5 shrink-0 ${report.grounded ? 'text-verdant' : 'text-ash'}`}
          aria-hidden
        />
        <span className="text-[13px] text-ash">{sourceNote(report)}</span>
      </footer>
    </article>
  )
}
