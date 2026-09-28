import { CircleCheck, CircleDashed } from 'lucide-react'
import type { Schemas } from '@/lib/api-client'
import { formatCount, formatDate, formatShortDate } from '@/lib/format'

type Source = Schemas['SourceStatusOut']

const HEADER = 'font-mono text-[11px] tracking-[0.6px] text-ash uppercase'

/** What has been loaded per source. Trust checks join this table in Phase 4. */
export function SourcesTable({ sources }: { sources: Source[] }) {
  const loaded = sources.filter((s) => s.rows > 0).length
  return (
    <section className="flex flex-col gap-4">
      <h2 className="flex items-baseline gap-3 text-heading-sm font-normal">
        Sources
        <span className="font-mono text-[12px] text-ash">
          {loaded}/{sources.length}
        </span>
      </h2>
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-hairline">
            <th className={`${HEADER} py-2 font-normal`}>Source</th>
            <th className={`${HEADER} w-48 py-2 font-normal`}>Date range</th>
            <th className={`${HEADER} w-36 py-2 font-normal`}>Last day</th>
            <th className={`${HEADER} w-28 py-2 font-normal`}>Rows</th>
            <th className={`${HEADER} w-40 py-2 font-normal`}>Status</th>
          </tr>
        </thead>
        <tbody>
          {sources.map((source) => (
            <tr key={source.source} className="border-b border-hairline">
              <td className="py-3.5 text-ink">{source.label}</td>
              <td className="py-3.5 text-driftwood">
                {source.first_date && source.last_date
                  ? `${formatShortDate(source.first_date)} – ${formatShortDate(source.last_date)} · ${source.days} ${source.days === 1 ? 'day' : 'days'}`
                  : '—'}
              </td>
              <td className="py-3.5 text-driftwood">
                {source.last_date ? formatDate(source.last_date) : '—'}
              </td>
              <td className="py-3.5 text-driftwood">{formatCount(source.rows)}</td>
              <td className="py-3.5">
                {source.rows > 0 ? (
                  <span className="flex items-center gap-1.5 text-[13px] text-forest">
                    <CircleCheck className="size-3.5" aria-hidden />
                    Loaded
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5 text-[13px] text-ash">
                    <CircleDashed className="size-3.5" aria-hidden />
                    No data yet
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
