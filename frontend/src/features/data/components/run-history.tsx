import type { Schemas } from '@/lib/api-client'
import { formatDateTime } from '@/lib/format'
import { RunRow } from './run-row'

type RunHistoryProps = {
  runs: Schemas['IngestionRunOut'][]
  sourceLabels: Record<string, string>
}

export function RunHistory({ runs, sourceLabels }: RunHistoryProps) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-heading-sm font-normal">Recent imports</h2>
      {runs.length === 0 ? (
        <p className="text-driftwood">Nothing has been imported yet.</p>
      ) : (
        <ul className="border-t border-hairline">
          {runs.map((run) => (
            <RunRow
              key={run.id}
              run={run}
              sourceLabel={run.source ? sourceLabels[run.source] : undefined}
              lead={
                <span className="flex flex-col">
                  <span className="text-ink">{formatDateTime(run.created_at)}</span>
                  <span className="truncate font-mono text-[12px] text-driftwood">
                    {run.file_name}
                  </span>
                </span>
              }
            />
          ))}
        </ul>
      )}
    </section>
  )
}
