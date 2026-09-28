"""Recommendations (FR-9): one action from a fixed catalogue, with every number computed.

The action, the rupee range it could recover, the confidence, the risk, the KPI to watch
and the condition to stop on all come from here. The LLM may choose *which* catalogue
action fits and say why, but it can neither invent an action nor supply a number, and
the protected-campaign guardrail is enforced in code whatever it chooses (FR-9.4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, get_args

from mdia.domain.diagnosis import dominant_chain, value_text
from mdia.domain.kpi import label

if TYPE_CHECKING:
    from collections.abc import Mapping

    from mdia.domain.diagnosis import Cause, Diagnosis, Evidence
    from mdia.domain.kpi import Metric
    from mdia.domain.signals import EntityLevel
    from mdia.domain.trust import TrustStatus

# FR-9.1. Nothing outside this list may ever be recommended.
Action = Literal[
    "pause_creative",
    "rotate_creative",
    "refine_audience",
    "investigate_landing_page",
    "fix_tracking",
    "shift_budget",
    "adjust_pacing",
]
ACTION_TYPES: tuple[Action, ...] = get_args(Action)

Risk = Literal["low", "medium", "high"]

# Actions that stop spend outright, so a protected campaign may never receive one.
HALTING: frozenset[Action] = frozenset({"pause_creative"})

# Confidence terms (FR-9.3) and their weights; they sum to 1. The floor keeps a
# weak-but-real finding from arriving as "no confidence at all".
WEIGHT_STRENGTH = 0.35
WEIGHT_AGREEMENT = 0.20
WEIGHT_SHARE = 0.20
WEIGHT_TRUST = 0.25
MIN_CONFIDENCE = 0.10
# A move this big is as strong as the term gets, and this many agreeing signals as broad.
STRONG_CHANGE_PCT = 50.0
AGREEING_SIGNALS = 3
# No decomposition means the share term carries no information either way.
NEUTRAL_SHARE = 0.5

_TRUST_TERM: dict[TrustStatus, float] = {"ok": 1.0, "warning": 0.5, "broken": 0.1}


@dataclass(frozen=True, slots=True)
class ActionSpec:
    """What an action needs and what it is worth, so neither is a judgement call."""

    risk: Risk
    # The entity levels the action can actually be taken on.
    levels: tuple[EntityLevel, ...]
    # Parameters the platform change cannot be made without; a missing one voids the action.
    params: tuple[str, ...]
    # Share of the rupees at stake the action could plausibly recover, low to high.
    recovery: tuple[float, float]
    # What to watch instead of the opportunity's own metric, when they differ.
    watch: Metric | None = None


ACTIONS: dict[Action, ActionSpec] = {
    "pause_creative": ActionSpec("high", ("creative",), ("creative_id",), (0.4, 0.9)),
    "rotate_creative": ActionSpec("medium", ("creative",), ("creative_id",), (0.3, 0.7)),
    "refine_audience": ActionSpec(
        "medium", ("age_group", "ad_set", "campaign"), ("ad_set_id",), (0.2, 0.5)
    ),
    "investigate_landing_page": ActionSpec(
        "low", ("account", "channel", "campaign", "source"), (), (0.3, 0.8), watch="web_cvr"
    ),
    "fix_tracking": ActionSpec("low", ("account", "channel", "source"), ("channel",), (0.0, 0.0)),
    "shift_budget": ActionSpec(
        "medium", ("account", "channel", "campaign"), ("direction",), (0.2, 0.6)
    ),
    "adjust_pacing": ActionSpec("low", ("account", "channel"), ("channel",), (0.1, 0.4)),
}

# Which actions answer which cause, best first; the first allowed one is recommended.
CAUSE_ACTIONS: dict[Cause, tuple[Action, ...]] = {
    "creative_fatigue": ("rotate_creative", "pause_creative", "refine_audience"),
    "landing_page_break": ("investigate_landing_page",),
    "cpc_spike": ("shift_budget", "refine_audience"),
    "audience_mismatch": ("refine_audience",),
    "tracking_break": ("fix_tracking",),
    "budget_overpace": ("adjust_pacing",),
    "channel_opportunity": ("shift_budget",),
    "conversion_drop": ("investigate_landing_page", "refine_audience"),
    "unknown": (),
}

# The sentence that turns a hypothesis into a reason for acting, when the rules choose.
_ANSWERS: dict[Action, str] = {
    "pause_creative": "Stopping it keeps the rest of the budget away from it.",
    "rotate_creative": "A fresh creative to the same audience is the cheapest way to test that.",
    "refine_audience": "Narrowing the audience is the change that would act on it.",
    "investigate_landing_page": "The page has to be checked before any ad change would help.",
    "fix_tracking": "Nothing else should be changed until the numbers can be trusted again.",
    "shift_budget": "Moving budget is the change that acts on it without touching the ads.",
    "adjust_pacing": "Lowering the daily cap brings the month back onto plan.",
}


@dataclass(frozen=True, slots=True)
class Recommendation:
    """One action to take, with everything FR-9.2 asks it to carry."""

    action: Action
    rationale: str
    # The rupees this could recover over a window, low to high. Never from the LLM.
    expected_impact: tuple[float, float]
    confidence: float
    risk: Risk
    watch: Metric
    stop_condition: str
    params: Mapping[str, str]


def allowed(action: Action, evidence: Evidence) -> bool:
    """Whether the action can be taken on this entity at all (FR-9.4 guardrail included)."""
    spec = ACTIONS.get(action)
    if spec is None:
        return False
    if evidence.protected and action in HALTING:
        return False
    return evidence.entity.level in spec.levels and valid(action, params_for(action, evidence))


def valid(action: Action, params: Mapping[str, str]) -> bool:
    """Whether every parameter the platform change needs is filled in."""
    spec = ACTIONS.get(action)
    if spec is None:
        return False
    return all(params.get(name) for name in spec.params)


def params_for(action: Action, evidence: Evidence) -> dict[str, str]:
    """The parameters of the change, read off the entity the action applies to."""
    entity = evidence.entity
    found = {"target_level": entity.level, "target_key": entity.key}
    if entity.channel:
        found["channel"] = entity.channel
    for level in ("creative", "ad_set", "campaign"):
        key = _own_or_ancestor(evidence, level)
        if key is not None:
            found[f"{level}_id"] = key
    if action == "shift_budget":
        found["direction"] = "into" if evidence.kind == "win" else "out_of"
    return found


def choose(diagnosis: Diagnosis, evidence: Evidence) -> Action | None:
    """The best catalogue action for the leading hypothesis that this entity allows."""
    for hypothesis in diagnosis.hypotheses:
        for action in CAUSE_ACTIONS.get(hypothesis.cause, ()):
            if allowed(action, evidence):
                return action
    return None


def confidence(*, strength: float, agreement: float, share: float, trust: float) -> float:
    """FR-9.3, with every term in 0-1 and the result monotonic in each of them."""
    blended = (
        WEIGHT_STRENGTH * _clamp(strength)
        + WEIGHT_AGREEMENT * _clamp(agreement)
        + WEIGHT_SHARE * _clamp(share)
        + WEIGHT_TRUST * _clamp(trust)
    )
    return round(MIN_CONFIDENCE + (1 - MIN_CONFIDENCE) * blended, 4)


def confidence_of(evidence: Evidence) -> float:
    """The confidence terms as this evidence supplies them."""
    chain = dominant_chain(evidence.tree)
    return confidence(
        strength=abs(evidence.primary.change_pct or 0.0) / STRONG_CHANGE_PCT,
        agreement=(len(evidence.signals) - 1) / AGREEING_SIGNALS,
        share=abs(chain[-1].share_pct or 0.0) / 100 if chain else NEUTRAL_SHARE,
        trust=_TRUST_TERM[evidence.trust],
    )


def priority(impact: float, confidence_value: float) -> float:
    """FR-9.4: what to do first is what is at stake times how sure of it we are."""
    return impact * confidence_value


def recommend(
    diagnosis: Diagnosis,
    evidence: Evidence,
    *,
    action: Action | None = None,
    rationale: str = "",
) -> Recommendation | None:
    """Build the recommendation for a diagnosis; ``None`` when no action applies.

    ``action`` and ``rationale`` are the LLM's choice where it had one. An action it is
    not allowed to take on this entity is dropped, and the rules choose instead.
    """
    from_llm = action is not None and allowed(action, evidence)
    chosen = action if from_llm else choose(diagnosis, evidence)
    if chosen is None:
        return None
    spec = ACTIONS[chosen]
    low, high = spec.recovery
    watch = spec.watch or evidence.primary.metric
    return Recommendation(
        action=chosen,
        rationale=rationale if from_llm and rationale else _rationale(diagnosis, chosen),
        expected_impact=(evidence.impact * low, evidence.impact * high),
        confidence=confidence_of(evidence),
        risk=spec.risk,
        watch=watch,
        stop_condition=_stop_condition(watch, evidence),
        params=params_for(chosen, evidence),
    )


def _rationale(diagnosis: Diagnosis, action: Action) -> str:
    """Why this action, when the rules picked it: the leading hypothesis, restated."""
    return f"{diagnosis.hypotheses[0].statement} {_ANSWERS[action]}"


def _stop_condition(watch: Metric, evidence: Evidence) -> str:
    """When to call the change off, in terms of the metric being watched."""
    baseline = evidence.primary.baseline
    if watch != evidence.primary.metric or baseline is None:
        return f"Stop if {label(watch)} has not recovered within {evidence.window.days} days."
    return (
        f"Stop if {label(watch)} is no better than {value_text(watch, baseline)}"
        f" after {evidence.window.days} days."
    )


def _own_or_ancestor(evidence: Evidence, level: str) -> str | None:
    """The entity's key at ``level``, whether that is itself or something above it."""
    entity = evidence.entity
    if entity.level == level:
        return entity.key
    prefix = f"{level}:"
    return next(
        (ancestor[len(prefix) :] for ancestor in entity.ancestors if ancestor.startswith(prefix)),
        None,
    )


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
