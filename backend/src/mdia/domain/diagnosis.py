"""Evidence and the rule-based diagnosis (FR-8.1, FR-8.4).

The evidence tree is arithmetic: the KPI that moved, broken into the drivers that moved
it and each driver's share of the change, down to the level where a driver has no
formula of its own. The rules then read the shape of that tree and name what it is
*consistent with* — a tired creative and a costlier auction both raise CPA, and it is
the tree that says which of them the numbers look like.

Nothing here asserts a cause (FR-8.4), and nothing here is optional: this is also the
fallback the investigation graph uses whenever the LLM is unavailable or ungrounded.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, TypeGuard

from mdia.domain.decomposition import FORMULAS, decompose
from mdia.domain.kpi import change_pct, label, metric_values

if TYPE_CHECKING:
    from collections.abc import Collection, Iterator, Mapping, Sequence

    from mdia.domain.kpi import Kpi, Metric
    from mdia.domain.opportunities import Opportunity, OpportunityKind
    from mdia.domain.periods import Period
    from mdia.domain.signals import Entity, Signal
    from mdia.domain.trust import TrustStatus

# The fixed list a hypothesis has to choose from (FR-8.2); the LLM may not invent one.
Cause = Literal[
    "creative_fatigue",
    "landing_page_break",
    "cpc_spike",
    "audience_mismatch",
    "tracking_break",
    "budget_overpace",
    "channel_opportunity",
    "conversion_drop",
    "unknown",
]

CAUSE_LABELS: dict[Cause, str] = {
    "creative_fatigue": "Creative fatigue",
    "landing_page_break": "Landing page problem",
    "cpc_spike": "Rising auction cost",
    "audience_mismatch": "Audience mismatch",
    "tracking_break": "Broken conversion tracking",
    "budget_overpace": "Spending ahead of budget",
    "channel_opportunity": "Room to scale",
    "conversion_drop": "Fewer clicks converting",
    "unknown": "Not clear from the data",
}

# How deep the tree goes: CPA → CPC → CPM and CTR is as far as the formulas reach.
MAX_DEPTH = 2
# A driver owns the movement once it accounts for this much of it.
DOMINANT_SHARE = 60.0
# How much a metric has to move before "frequency is climbing" is worth mentioning.
SUPPORTING_PCT = 10.0

_PERCENT: frozenset[str] = frozenset(
    {"ctr", "cvr", "web_cvr", "bounce_rate", "atc_rate", "checkout_rate", "purchase_rate"}
)
_MULTIPLE: frozenset[str] = frozenset({"roas", "mer", "frequency"})


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
    """Everything the diagnosis is allowed to be built from — LLM or rules."""

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


@dataclass(frozen=True, slots=True)
class Hypothesis:
    """One reading of the evidence, ranked against the others."""

    cause: Cause
    statement: str
    signal_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Diagnosis:
    observation: str
    hypotheses: tuple[Hypothesis, ...]
    alternatives: tuple[str, ...]


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


def diagnose(evidence: Evidence) -> Diagnosis:
    """Rank what the evidence is consistent with (FR-8.3's fallback)."""
    ranked = sorted(_candidates(evidence), key=lambda candidate: -candidate[0])
    hypotheses = tuple(hypothesis for _, hypothesis in ranked) or (_unknown(evidence),)
    return Diagnosis(
        observation=observation(evidence),
        hypotheses=hypotheses,
        alternatives=alternatives(evidence),
    )


def observation(evidence: Evidence) -> str:
    """What happened, in one sentence of numbers that are all computed."""
    signal = evidence.primary
    window = evidence.window
    moved = _moved(signal.change_pct)
    at = "" if signal.current is None else f" to {value_text(signal.metric, signal.current)}"
    return (
        f"{evidence.entity.name}: {label(signal.metric)} {moved}{at}"
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


def value_text(metric: Metric, value: float) -> str:
    """A metric's value in the unit it is read in: a rate, a multiple or rupees."""
    if metric in _PERCENT:
        return f"{as_shown(metric, value):.2f}%"
    if metric in _MULTIPLE:
        return f"{value:.2f}x"
    return rupees(value)


def as_shown(metric: Metric, value: float) -> float:
    """The number a reader actually sees: a rate as a percentage, anything else as it is.

    The grounding guard needs this to tell a copied number from an invented one.
    """
    return value * 100 if metric in _PERCENT else value


def rupees(value: float) -> str:
    """Rupees in the unit an Indian operator reads them in."""
    if abs(value) >= 1e7:
        return f"₹{value / 1e7:.2f} Cr"
    if abs(value) >= 1e5:
        return f"₹{value / 1e5:.2f} L"
    return f"₹{value:,.0f}"


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


def _candidates(evidence: Evidence) -> Iterator[tuple[float, Hypothesis]]:
    """Every reading the rules recognise, each with how well the evidence fits it."""
    chain = {node.metric: node for node in dominant_chain(evidence.tree)}
    detector = evidence.primary.detector
    if detector == "tracking_break":
        yield (
            1.0,
            _hypothesis(
                "tracking_break",
                f"Reported conversions are running at {evidence.primary.current or 0:.0%}"
                " of this channel's usual rate against store orders.",
                evidence,
                detectors={"tracking_break"},
            ),
        )
    if detector == "goal_breach" and evidence.primary.metric == "spend":
        yield (
            1.0,
            _hypothesis(
                "budget_overpace",
                f"Spend is running at {_rate(evidence.primary.current)} a day against the"
                f" {_rate(evidence.primary.baseline)} the month's budget allows.",
                evidence,
                detectors={"goal_breach"},
            ),
        )
    if evidence.kind == "win":
        yield (
            0.9,
            _hypothesis(
                "channel_opportunity",
                f"{label(evidence.primary.metric)} is ahead of its own baseline while spend"
                " is unchanged, so there is room to buy more of the same.",
                evidence,
            ),
        )
        return
    if _any(evidence, "segment_divergence"):
        yield (
            0.8,
            _hypothesis(
                "audience_mismatch",
                "This age group is performing worse than the rest of its ad set on the same"
                " creative and budget.",
                evidence,
                detectors={"segment_divergence"},
            ),
        )
    if _any(evidence, "funnel_drop"):
        yield (
            0.8,
            _hypothesis(
                "landing_page_break",
                "A step of the site funnel fell for these sessions, so fewer of the clicks"
                " already paid for reach checkout.",
                evidence,
                detectors={"funnel_drop"},
            ),
        )
    if "ctr" in chain and (chain["ctr"].change_pct or 0.0) < 0:
        yield (
            0.7 + _bonus(evidence, "frequency"),
            _hypothesis(
                "creative_fatigue",
                f"CTR fell {abs(chain['ctr'].change_pct or 0.0):.0f}% and took CPC with it,"
                " which is what an audience that has seen the ad too often looks like.",
                evidence,
                metrics={"ctr", "frequency", "cpc"},
            ),
        )
    if "cpm" in chain and (chain["cpm"].change_pct or 0.0) > 0:
        yield (
            0.7,
            _hypothesis(
                "cpc_spike",
                f"CPM rose {chain['cpm'].change_pct or 0.0:.0f}% with CTR holding, so the"
                " auction is charging more for the same attention.",
                evidence,
                metrics={"cpm", "cpc"},
            ),
        )
    if "cvr" in chain and (chain["cvr"].change_pct or 0.0) < 0:
        yield (
            0.5,
            _hypothesis(
                "conversion_drop",
                f"{abs(chain['cvr'].change_pct or 0.0):.0f}% fewer clicks are converting,"
                " while the cost of the clicks themselves held.",
                evidence,
                metrics={"cvr"},
            ),
        )
    if "cpc" in chain and not chain.keys() & {"cpm", "ctr"}:
        yield (
            0.4,
            _hypothesis(
                "cpc_spike",
                f"CPC rose {chain['cpc'].change_pct or 0.0:.0f}% and carried the whole move.",
                evidence,
                metrics={"cpc"},
            ),
        )


def _hypothesis(
    cause: Cause,
    statement: str,
    evidence: Evidence,
    *,
    detectors: Collection[str] = (),
    metrics: Collection[str] = (),
) -> Hypothesis:
    """A hypothesis carrying the signal IDs it rests on (NFR-3)."""
    cited = tuple(
        signal.id
        for signal in evidence.signals
        if signal.detector in detectors or signal.metric in metrics
    )
    return Hypothesis(cause, statement, cited or (evidence.primary.id,))


def _unknown(evidence: Evidence) -> Hypothesis:
    return Hypothesis(
        "unknown",
        "The move is real but no single driver accounts for it, so there is nothing here"
        " to act on yet.",
        (evidence.primary.id,),
    )


def _any(evidence: Evidence, detector: str) -> bool:
    return any(signal.detector == detector for signal in evidence.signals)


def _bonus(evidence: Evidence, metric: Metric) -> float:
    """A nudge for a second signal that points the same way."""
    moved = any(
        signal.metric == metric and abs(signal.change_pct or 0.0) >= SUPPORTING_PCT
        for signal in evidence.signals
    )
    return 0.1 if moved else 0.0


def _moved(change: float | None) -> str:
    if change is None:
        return "moved"
    return f"{'rose' if change > 0 else 'fell'} {abs(change):.0f}%"


def _rate(value: float | None) -> str:
    return "an unknown amount" if value is None else rupees(value)
