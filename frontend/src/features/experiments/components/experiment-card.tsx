import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { actionLabel } from '@/lib/actions'
import { formatMetric } from '@/lib/metrics'
import { entityLine } from '@/lib/opportunities'
import { movementText, watchLine, type Experiment } from '@/lib/experiments'
import { Eyebrow } from '@/components/common/section'

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1 border-l border-hairline px-4 first:border-l-0 first:pl-0">
      <Eyebrow>{label}</Eyebrow>
      <span className="text-[13px] text-ink">{children}</span>
    </div>
  )
}

type ExperimentCardProps = {
  experiment: Experiment
  /** The tab's own row: Approve / Reject, the progress bar, or the verdict. */
  children?: ReactNode
}

/** One experiment: where it came from, what it claims, and the numbers it is judged on. */
export function ExperimentCard({ experiment, children }: ExperimentCardProps) {
  const { opportunity } = experiment
  return (
    <article className="flex flex-col gap-5 rounded-lg border border-hairline bg-bone p-7">
      <div className="flex flex-col gap-2">
        <span className="font-mono text-[11px] tracking-[0.6px] text-ash">
          {entityLine(opportunity)}
        </span>
        <h3 className="text-heading-sm font-normal text-ink">{actionLabel(experiment.action)}</h3>
        <p className="font-serif text-[17px] leading-[1.45] text-driftwood">
          {experiment.hypothesis}
        </p>
        <Link
          to={`/opportunities/${opportunity.id}`}
          className="text-[13px] text-ember hover:underline"
        >
          Why this was raised: {opportunity.title}
        </Link>
      </div>
      <div className="grid grid-cols-4 border-t border-hairline pt-3.5">
        <Fact label="Metric">{movementText(experiment)}</Fact>
        <Fact label="Baseline">{formatMetric(experiment.metric, experiment.baseline)}</Fact>
        <Fact label="Target">
          {experiment.target === null
            ? 'Any improvement'
            : formatMetric(experiment.metric, experiment.target)}
        </Fact>
        <Fact label="Duration">{experiment.duration_days} days</Fact>
      </div>
      <p className="text-[13px] text-ash">{watchLine(experiment)}</p>
      {children}
    </article>
  )
}
