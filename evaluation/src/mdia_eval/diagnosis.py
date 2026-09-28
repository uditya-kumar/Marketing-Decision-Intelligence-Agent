"""Diagnosis accuracy (FR-13.2): is the injected cause in the ranked hypotheses?

Each detected scenario is investigated again exactly as the backend would, then the
ranked causes are compared with what the generator actually did. The same cases run
twice — once with the model and once without — so the LLM's ranking can be read against
the rules it falls back to.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from mdia.agents.investigation import build_investigation, investigate

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from langchain_core.language_models import BaseChatModel
    from mdia.agents.investigation import Investigation
    from mdia.agents.llm import CallRecord
    from mdia.domain.diagnosis import Cause
    from mdia.domain.opportunities import Opportunity
    from mdia.domain.recommendations import Action
    from mdia.domain.trust import TrustStatus

    from mdia_eval.detection import Score
    from mdia_eval.replay import Run
    from mdia_eval.truth import Event

# §13 reads diagnosis as "the right cause among the top three".
TARGET_TOP3 = 0.80
TOP_N = 3

# The generator names two actions from the simulation's side; FR-9.1 names them from the
# operator's. Same change, different vocabulary.
ACTION_ALIASES: dict[str, Action] = {
    "retarget_audience": "refine_audience",
    "budget_shift": "shift_budget",
}


@dataclass(frozen=True, slots=True)
class Case:
    """One detected scenario, diagnosed: what was injected against what was said."""

    event_id: str
    kind: str
    causes: tuple[Cause, ...]
    action: Action | None
    expected_action: Action | None
    source: str

    @property
    def top1(self) -> bool:
        return bool(self.causes) and self.causes[0] == self.kind

    @property
    def top3(self) -> bool:
        return self.kind in self.causes[:TOP_N]

    @property
    def action_right(self) -> bool | None:
        """``None`` when ground truth expects no particular action."""
        return None if self.expected_action is None else self.action == self.expected_action


@dataclass(frozen=True, slots=True)
class DiagnosisScore:
    """FR-13.2 for one source of hypotheses, the rules or the model."""

    source: str
    cases: list[Case] = field(default_factory=list)
    # Every model call the run made, for the grounding report (FR-13.4): nothing logs
    # these to the database, because the graph is driven here and not by a request.
    calls: list[CallRecord] = field(default_factory=list)

    @property
    def top1(self) -> float:
        return _ratio(sum(case.top1 for case in self.cases), len(self.cases))

    @property
    def top3(self) -> float:
        return _ratio(sum(case.top3 for case in self.cases), len(self.cases))

    @property
    def action_accuracy(self) -> float:
        judged = [case for case in self.cases if case.action_right is not None]
        return _ratio(sum(bool(case.action_right) for case in judged), len(judged))

    @property
    def missed(self) -> list[Case]:
        return [case for case in self.cases if not case.top3]

    def by_kind(self) -> dict[str, tuple[int, int, int]]:
        """Scenario type → (top-1 hits, top-3 hits, cases)."""
        counts: dict[str, list[int]] = {}
        for case in self.cases:
            row = counts.setdefault(case.kind, [0, 0, 0])
            row[0] += case.top1
            row[1] += case.top3
            row[2] += 1
        return {kind: (one, three, total) for kind, (one, three, total) in sorted(counts.items())}


def score(
    runs: Sequence[Run],
    detection: Score,
    *,
    model: BaseChatModel | None = None,
    limit: int | None = None,
) -> DiagnosisScore:
    """Diagnose every detected scenario; ``model`` of ``None`` scores the rules alone."""
    graph = build_investigation(model)
    cases: list[Case] = []
    calls: list[CallRecord] = []
    for event, opportunity, trust in _subjects(runs, detection, limit):
        investigation = investigate(graph, opportunity, trust=trust)
        cases.append(_case(event, investigation))
        calls.extend(investigation.calls)
    return DiagnosisScore(source="llm" if model is not None else "rules", cases=cases, calls=calls)


def _subjects(
    runs: Sequence[Run], detection: Score, limit: int | None
) -> Iterator[tuple[Event, Opportunity, TrustStatus]]:
    """The opportunity each scenario was first raised as, with the trust of its channel."""
    by_day = {(run.as_of, o.key): (o, run) for run in runs for o in run.opportunities}
    pairs = sorted(detection.detected, key=lambda pair: pair[1].detected_on)[:limit]
    for event, episode in pairs:
        found = by_day.get((episode.detected_on, episode.key))
        if found is None:  # pragma: no cover - an episode always comes from a run
            continue
        opportunity, run = found
        yield event, opportunity, _trust(run, opportunity)


def _trust(run: Run, opportunity: Opportunity) -> TrustStatus:
    """What the trust checks said about the channel paying for this entity, that day."""
    channel = opportunity.entity.channel
    check = run.tracking.get(channel) if channel else None
    return check.status if check else "ok"


def _case(event: Event, investigation: Investigation) -> Case:
    recommendation = investigation.recommendation
    return Case(
        event_id=event.id,
        kind=event.kind,
        causes=tuple(h.cause for h in investigation.diagnosis.hypotheses),
        action=recommendation.action if recommendation else None,
        expected_action=expected_action(event),
        source=investigation.source,
    )


def expected_action(event: Event) -> Action | None:
    """Ground truth's action name, in FR-9.1's vocabulary."""
    name = event.expected_action
    if name is None:
        return None
    alias = ACTION_ALIASES.get(name)
    return alias if alias else cast("Action", name)


def _ratio(part: int, whole: int) -> float:
    return 0.0 if whole == 0 else part / whole
