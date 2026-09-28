import { progressPct, progressText, type Experiment } from '@/lib/experiments'

/** "Day 4 of 7" with the bar the Running tab shows (UI.md §5.4). */
export function ProgressBar({ progress }: { progress: NonNullable<Experiment['progress']> }) {
  const pct = progressPct(progress)
  return (
    <div className="flex flex-col gap-2 border-t border-hairline pt-5">
      <div className="flex items-center justify-between text-[13px]">
        <span className="text-ink">{progressText(progress)}</span>
        <span className="text-ash">
          {progress.due ? 'Ready to judge' : 'Upload next week to see how it went'}
        </span>
      </div>
      <div
        role="progressbar"
        aria-label="Days elapsed"
        aria-valuenow={progress.day}
        aria-valuemin={0}
        aria-valuemax={progress.total}
        className="h-1.5 w-full overflow-hidden rounded-full bg-linen"
      >
        <div className="h-full rounded-full bg-ember" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
