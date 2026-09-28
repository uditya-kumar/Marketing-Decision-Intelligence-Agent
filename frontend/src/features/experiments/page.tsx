import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FlaskConical } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/common/empty-state'
import { ErrorState } from '@/components/common/error-state'
import { PageHeader } from '@/components/common/page-header'
import { SegmentedControl } from '@/components/common/segmented-control'
import {
  experimentsSummary,
  filterExperiments,
  firstFilledTab,
  type Experiment,
  type ExperimentTab,
} from '@/lib/experiments'
import { useExperiments } from './api'
import { DecideForm } from './components/decide-form'
import { ExperimentCard } from './components/experiment-card'
import { Outcome } from './components/outcome'
import { ProgressBar } from './components/progress-bar'

const LABELS: Record<ExperimentTab, string> = {
  awaiting: 'Awaiting approval',
  running: 'Running',
  completed: 'Completed',
}

const EMPTY: Record<ExperimentTab, string> = {
  awaiting: 'Nothing is waiting on you. Create an experiment from an opportunity to see it here.',
  running: 'No change is being measured right now.',
  completed: 'Nothing has finished yet. A verdict lands once the week it runs over is uploaded.',
}

function CardsSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      {Array.from({ length: 2 }, (_, row) => (
        <Skeleton key={row} className="h-64" />
      ))}
    </div>
  )
}

/** The tab's own row under the card: the decision, the progress, or the verdict. */
function Footer({ experiment }: { experiment: Experiment }) {
  if (experiment.status === 'draft') return <DecideForm id={experiment.id} />
  if (experiment.status === 'running') {
    return experiment.progress === null ? null : <ProgressBar progress={experiment.progress} />
  }
  return <Outcome experiment={experiment} />
}

export default function ExperimentsPage() {
  const experiments = useExperiments()
  // Until the reader picks a tab, the data picks it.
  const [picked, setTab] = useState<ExperimentTab | null>(null)

  if (experiments.isError) {
    return <ErrorState message="We couldn't load your experiments." onRetry={experiments.refetch} />
  }

  const rows = experiments.data
  const tab = picked ?? (rows ? firstFilledTab(rows) : 'awaiting')
  const options = (Object.keys(LABELS) as ExperimentTab[]).map((value) => ({
    value,
    label: LABELS[value],
    count: rows && filterExperiments(rows, value).length,
  }))
  const shown = rows ? filterExperiments(rows, tab) : []

  return (
    <>
      <PageHeader title="Experiments" summary={rows && experimentsSummary(rows)} />
      {rows?.length === 0 ? (
        <EmptyState
          icon={FlaskConical}
          message="An experiment starts from an opportunity: open one and create it from the recommended action."
          action={
            <Button asChild>
              <Link to="/opportunities">See opportunities</Link>
            </Button>
          }
        />
      ) : (
        <>
          <SegmentedControl
            label="Filter experiments"
            options={options}
            value={tab}
            onChange={setTab}
          />
          {!rows ? (
            <CardsSkeleton />
          ) : shown.length === 0 ? (
            <EmptyState icon={FlaskConical} message={EMPTY[tab]} />
          ) : (
            <div className="flex flex-col gap-6">
              {shown.map((experiment) => (
                <ExperimentCard key={experiment.id} experiment={experiment}>
                  <Footer experiment={experiment} />
                </ExperimentCard>
              ))}
            </div>
          )}
        </>
      )}
    </>
  )
}
