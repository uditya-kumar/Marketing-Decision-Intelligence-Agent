import { Skeleton } from '@/components/ui/skeleton'
import { TrustBadge } from '@/components/common/trust-badge'
import type { Schemas } from '@/lib/api-client'
import { formatCount, formatDate, formatShortDate } from '@/lib/format'
import { trustSummary } from '@/lib/trust'

type Source = Schemas['SourceStatusOut']
type SourceTrust = Schemas['SourceTrustOut']

const HEADER = 'font-mono text-[11px] tracking-[0.6px] text-ash uppercase'

type SourcesTableProps = {
  sources: Source[]
  /** Trust per source; `undefined` while the checks are still loading. */
  trust?: SourceTrust[]
}

/** What has been loaded per source, and whether each can be trusted. */
export function SourcesTable({ sources, trust }: SourcesTableProps) {
  const loaded = sources.filter((s) => s.rows > 0).length
  const trustBySource = new Map(trust?.map((t) => [t.source, t]))
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
            <th className={`${HEADER} w-64 py-2 font-normal`}>Trust</th>
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
                <SourceTrustCell
                  trust={trust && trustBySource.get(source.source)}
                  loading={!trust}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

function SourceTrustCell({ trust, loading }: { trust?: SourceTrust; loading: boolean }) {
  if (trust) return <TrustBadge {...trustSummary(trust)} />
  if (loading) return <Skeleton className="h-4 w-20" />
  return <span className="text-[13px] text-ash">—</span>
}
