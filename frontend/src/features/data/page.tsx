import { Skeleton } from '@/components/ui/skeleton'
import { ErrorState } from '@/components/common/error-state'
import { PageHeader } from '@/components/common/page-header'
import type { Schemas } from '@/lib/api-client'
import { formatDate } from '@/lib/format'
import { useIngestionRuns, useIngestionStatus, useTemplates, useTrust } from './api'
import { RunHistory } from './components/run-history'
import { SourcesTable } from './components/sources-table'
import { TemplateLinks } from './components/template-links'
import { UploadZone } from './components/upload-zone'

function summary(status: Schemas['IngestionStatusOut']): string {
  const loaded = status.sources.filter((s) => s.rows > 0).length
  if (loaded === 0) return 'Upload your ad, analytics and store exports to see your first numbers.'
  const missing = status.sources.filter((s) => s.rows === 0).map((s) => s.label)
  const through = status.as_of_date ? `, complete through ${formatDate(status.as_of_date)}` : ''
  if (missing.length === 0) return `All ${loaded} sources are loaded${through}.`
  return `${loaded} of ${status.sources.length} sources loaded${through}. Still missing: ${missing.join(', ')}.`
}

export default function DataPage() {
  const status = useIngestionStatus()
  const runs = useIngestionRuns()
  const templates = useTemplates()
  const trust = useTrust()

  if (status.isError) {
    return <ErrorState message="We couldn't load your data sources." onRetry={status.refetch} />
  }
  if (!status.data) {
    return (
      <>
        <Skeleton className="h-24 w-2/3" />
        <Skeleton className="h-44" />
        <Skeleton className="h-56" />
      </>
    )
  }

  const sourceLabels = Object.fromEntries(status.data.sources.map((s) => [s.source, s.label]))
  return (
    <>
      <PageHeader title="Data" summary={summary(status.data)}>
        {templates.data && <TemplateLinks templates={templates.data} />}
      </PageHeader>
      <UploadZone sourceLabels={sourceLabels} />
      <SourcesTable sources={status.data.sources} trust={trust.data?.sources} />
      {runs.isError ? (
        <ErrorState message="We couldn't load the import history." onRetry={runs.refetch} />
      ) : runs.data ? (
        <RunHistory runs={runs.data} sourceLabels={sourceLabels} />
      ) : (
        <Skeleton className="h-40" />
      )}
    </>
  )
}
