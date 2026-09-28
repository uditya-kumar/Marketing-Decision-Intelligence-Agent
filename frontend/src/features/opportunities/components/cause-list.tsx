import type { Schemas } from '@/lib/api-client'

type Hypothesis = Schemas['HypothesisOut']

function rank(index: number): string {
  return String(index + 1).padStart(2, '0')
}

type CauseListProps = {
  hypotheses: Hypothesis[]
  /** Explanations the evidence argues against, kept visible so the reader can disagree. */
  alternatives: string[]
}

/** The ranked causes, then the ones the numbers make less likely (UI.md §5.2). */
export function CauseList({ hypotheses, alternatives }: CauseListProps) {
  if (hypotheses.length === 0) {
    return (
      <p className="text-[13px] text-ash">
        No cause was worked out for this one. It scored too low to be investigated in the last run.
      </p>
    )
  }
  const [leading, ...rest] = hypotheses
  return (
    <div className="flex flex-col gap-7">
      <div className="flex gap-4">
        <span className="font-mono text-[12px] text-ember">{rank(0)}</span>
        <div className="flex flex-col gap-1.5">
          <h3 className="text-heading-sm font-normal text-ink">{leading.cause_label}</h3>
          <p className="font-serif text-[17px] leading-[1.45] text-driftwood">
            {leading.statement}
          </p>
        </div>
      </div>
      {[
        ...rest.map((hypothesis) => ({
          title: hypothesis.cause_label,
          body: hypothesis.statement,
        })),
        ...alternatives.map((alternative) => ({ title: undefined, body: alternative })),
      ].map((item, index) => (
        <div key={item.body} className="flex gap-4">
          <span className="font-mono text-[12px] text-mist">{rank(index + 1)}</span>
          <div className="flex flex-col gap-1">
            {item.title && (
              <p className="text-ink">
                {item.title} <span className="text-ash">· less likely</span>
              </p>
            )}
            <p className="text-[13px] text-ash">{item.body}</p>
          </div>
        </div>
      ))}
    </div>
  )
}
