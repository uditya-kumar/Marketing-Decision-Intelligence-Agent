"""The rule-based diagnosis (FR-8.4): what the evidence is *consistent with*.

A tired creative and a costlier auction both raise CPA, and it is the shape of the
evidence tree that says which of them the numbers look like. Nothing here asserts a
cause, and nothing here is optional: this is also the fallback the investigation graph
uses whenever the LLM is unavailable or ungrounded (FR-8.3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from mdia.domain.evidence import alternatives, dominant_chain, observation
from mdia.domain.kpi import label
from mdia.domain.wording import rupees

if TYPE_CHECKING:
    from collections.abc import Collection, Iterator

    from mdia.domain.evidence import Evidence
    from mdia.domain.kpi import Metric

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

# How much a metric has to move before "frequency is climbing" is worth mentioning.
SUPPORTING_PCT = 10.0


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


def diagnose(evidence: Evidence) -> Diagnosis:
    """Rank what the evidence is consistent with (FR-8.3's fallback)."""
    ranked = sorted(_candidates(evidence), key=lambda candidate: -candidate[0])
    hypotheses = tuple(hypothesis for _, hypothesis in ranked) or (_unknown(evidence),)
    return Diagnosis(
        observation=observation(evidence),
        hypotheses=hypotheses,
        alternatives=alternatives(evidence),
    )


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
    seen = any(
        signal.metric == metric and abs(signal.change_pct or 0.0) >= SUPPORTING_PCT
        for signal in evidence.signals
    )
    return 0.1 if seen else 0.0


def _rate(value: float | None) -> str:
    return "an unknown amount" if value is None else rupees(value)
