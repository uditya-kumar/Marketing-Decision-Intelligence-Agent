import { CornerDownRight } from 'lucide-react'
import { Delta } from '@/components/common/delta'
import type { Schemas } from '@/lib/api-client'
import { formatPercent } from '@/lib/format'
import { formatMetric, metricLabel, metricNote } from '@/lib/metrics'

type Node = Schemas['NodeOut']

const INDENT = 28
const SHARE_TRACK = 96

type Row = { node: Node; depth: number; parent: Node | null }

/** The tree as an indented list, parents before children (UI.md §5.2). */
function flatten(node: Node, depth = 0, parent: Node | null = null): Row[] {
  return [
    { node, depth, parent },
    ...node.children.flatMap((child) => flatten(child, depth + 1, node)),
  ]
}

function Share({ node, parent }: { node: Node; parent: Node | null }) {
  if (parent === null) {
    return <span className="font-mono text-[11px] text-mist">total</span>
  }
  // Below the split the share is no longer arithmetic, so the row says what it feeds instead.
  if (node.share_pct === null) {
    return (
      <span className="font-mono text-[11px] text-mist">drives {metricLabel(parent.metric)}</span>
    )
  }
  return (
    <>
      <span className="h-1 rounded-[1px] bg-linen" style={{ width: SHARE_TRACK }} aria-hidden>
        <span
          className="block h-full rounded-[1px] bg-ink"
          style={{ width: `${Math.min(Math.abs(node.share_pct), 100)}%` }}
        />
      </span>
      <span className="font-mono text-[11px] text-ash">
        {formatPercent(Math.abs(node.share_pct))} of change
      </span>
    </>
  )
}

export function EvidenceTree({ tree }: { tree: Node }) {
  // A goal read straight off one measure has nothing under it and no before to compare, so
  // a single row would only invite a comparison the numbers don't support.
  if (tree.children.length === 0 && tree.before === null) {
    return (
      <p className="text-[13px] text-ash">
        {metricLabel(tree.metric)} is measured on its own here, so there are no drivers to split it
        into.
      </p>
    )
  }
  return (
    <div className="flex flex-col">
      {flatten(tree).map(({ node, depth, parent }) => (
        <div
          key={`${depth}-${node.metric}`}
          className="flex items-center gap-5 border-b border-hairline py-3.5"
          style={{ paddingLeft: depth * INDENT }}
        >
          {depth > 0 && <CornerDownRight className="size-3.5 shrink-0 text-mist" aria-hidden />}
          <span className="flex min-w-0 flex-1 flex-col gap-0.5">
            <span className="font-medium text-ink">{metricLabel(node.metric)}</span>
            <span className="text-[12px] text-ash">{metricNote(node.metric)}</span>
          </span>
          <span className="w-[140px] shrink-0 font-mono text-[12px] text-driftwood">
            {formatMetric(node.metric, node.before)} → {formatMetric(node.metric, node.after)}
          </span>
          <Delta
            changePct={node.change_pct}
            higherIsBetter={node.higher_is_better}
            className="w-[70px] shrink-0"
          />
          <span className="flex w-[210px] shrink-0 items-center gap-2">
            <Share node={node} parent={parent} />
          </span>
        </div>
      ))}
    </div>
  )
}
