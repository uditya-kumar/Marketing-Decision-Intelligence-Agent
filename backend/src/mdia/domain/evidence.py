"""The evidence behind an opportunity (FR-8.1): arithmetic, and nothing interpreted.

The tree is the KPI that moved broken into the drivers that moved it, each with its
share of the change, down to the level where a driver has no formula of its own. It is
assembled once and then read by everything that explains the movement — the rules in
``diagnosis.py``, the prompt, the grounding guard and the API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeGuard

from mdia.domain.decomposition import FORMULAS, decompose
from mdia.domain.kpi import change_pct, label, metric_values
from mdia.domain.wording import moved, rupees, value_text

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from mdia.domain.kpi import Kpi, Metric
    from mdia.domain.opportunities import Opportunity, OpportunityKind
    from mdia.domain.periods import Period
    from mdia.domain.signals import Entity, Signal
    from mdia.domain.trust import TrustStatus

# How deep the tree goes: CPA → CPC → CPM and CTR is as far as the formulas reach.
MAX_DEPTH = 2
# A driver owns the movement once it accounts for this much of it.
DOMINANT_SHARE = 60.0


@dataclass(frozen=True, slots=True)
class Node:
    """One metric in the evidence tree, with its share of the change above it."""

    metric: Metric
    before: float | None
    after: float | None
    change_pct: float | None
    # Share of the parent's change this driver accounts for; ``None`` at the root.
    share_pct: float | None
    children: tuple[Node, ...] = ()


@dataclass(frozen=True, slots=True)
class Evidence:
    """Everything a diagnosis is allowed to be built from — LLM or rules."""

    entity: Entity
    window: Period
    kind: OpportunityKind
    # What happened: the signal that earned the opportunity its place.
    primary: Signal
    # Why, arithmetically. Rooted at the strongest metric that has a formula.
    tree: Node
    signals: tuple[Signal, ...]
    impact: float
    trust: TrustStatus
    # Inside a campaign the operator ring-fenced, so it may not be paused (FR-9.4).
    protected: bool

    @property
    def signal_ids(self) -> tuple[str, ...]:
        return tuple(signal.id for signal in self.signals)


def build_tree(
    metric: Metric,
    before: Mapping[str, float],
    after: Mapping[str, float],
) -> Node:
    """Decompose ``metric``'s move from the base measures of both windows (FR-8.1)."""
    return _node(metric, metric_values(before), metric_values(after), share=None, depth=0)


def build_evidence(
    opportunity: Opportunity,
    *,
    trust: TrustStatus = "ok",
    protected: Collection[str] = (),
) -> Evidence:
    """Assemble what an opportunity is known to be, before anyone interprets it."""
    root = _root(opportunity.signals)
    return Evidence(
        entity=opportunity.entity,
        window=opportunity.window,
        kind=opportunity.kind,
        primary=opportunity.primary,
        tree=build_tree(root.metric, root.baseline_measures, root.measures),
        signals=opportunity.signals,
        impact=opportunity.impact,
        trust=trust,
        protected=is_protected(opportunity.entity, protected),
    )


def is_protected(entity: Entity, protected: Collection[str]) -> bool:
    """Whether the entity is, or sits inside, a campaign the operator ring-fenced."""
    ids = {f"campaign:{value}" for value in protected}
    return entity.id in ids or bool(ids.intersection(entity.ancestors))


def dominant_chain(tree: Node) -> tuple[Node, ...]:
    """The drivers that each own the movement above them, from the root down.

    Empty when the change was shared out: two drivers at forty per cent each explain
    the move together, and neither of them is the story.
    """
    chain: list[Node] = []
    node = tree
    while node.children:
        best = max(node.children, key=lambda child: abs(child.share_pct or 0.0))
        if abs(best.share_pct or 0.0) < DOMINANT_SHARE:
            break
        chain.append(best)
        node = best
    return tuple(chain)


def observation(evidence: Evidence) -> str:
    """What happened, in one sentence of numbers that are all computed."""
    signal = evidence.primary
    window = evidence.window
    at = "" if signal.current is None else f" to {value_text(signal.metric, signal.current)}"
    return (
        f"{evidence.entity.name}: {label(signal.metric)} {moved(signal.change_pct)}{at}"
        f" over the {window.days} days to {window.end:%d %b}, "
        f"against {rupees(evidence.impact)} at stake."
    )


def alternatives(evidence: Evidence) -> tuple[str, ...]:
    """Readings the data cannot rule out, so the diagnosis is never read as proof."""
    found = ["Normal week-to-week variation, if the move does not hold next week."]
    if evidence.trust != "ok":
        found.append("A reporting problem rather than a real one: this channel's data is suspect.")
    if evidence.entity.level in {"creative", "ad_set", "age_group"}:
        found.append("Spend moving between this and its siblings, rather than its own performance.")
    return tuple(found)


def _node(
    metric: Metric,
    before: Mapping[Metric, float | None],
    after: Mapping[Metric, float | None],
    *,
    share: float | None,
    depth: int,
) -> Node:
    split = decompose(metric, before, after) if _decomposable(metric, depth) else None
    children = (
        tuple(
            _node(driver.metric, before, after, share=driver.share_pct, depth=depth + 1)
            for driver in split.drivers
        )
        if split
        else ()
    )
    return Node(
        metric=metric,
        before=before.get(metric),
        after=after.get(metric),
        change_pct=change_pct(before.get(metric), after.get(metric)),
        share_pct=share,
        children=children,
    )


def _decomposable(metric: Metric, depth: int) -> TypeGuard[Kpi]:
    return depth < MAX_DEPTH and metric in FORMULAS


def _root(signals: Sequence[Signal]) -> Signal:
    """The signal the tree is rooted at: the strongest one that can be decomposed.

    A creative's CTR may score higher than its CPA, but CTR has no formula, so rooting
    the tree there would say nothing about what the movement is made of.
    """
    decomposable = [
        signal for signal in signals if signal.metric in FORMULAS and signal.baseline_measures
    ]
    return max(decomposable, key=lambda signal: signal.score, default=signals[0])
