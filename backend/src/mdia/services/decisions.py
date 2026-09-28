"""The decision log (FR-10.4): every human call, with the chain that produced it.

Nothing is decided here — approving, rejecting and dismissing all happen in their own
services, which write the row. This is the read side: the timeline the screen groups by
month, each entry carrying the opportunity it answered and the experiment it made.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mdia.repositories.analysis import AnalysisRepository
from mdia.repositories.decisions import DecisionRepository
from mdia.services.experiment_rows import view
from mdia.services.opportunities import summary

if TYPE_CHECKING:
    import datetime as dt

    from sqlalchemy.orm import Session

    from mdia.models.experiments import DecisionKind
    from mdia.services.experiment_rows import ExperimentView
    from mdia.services.opportunities import OpportunitySummary


@dataclass(frozen=True, slots=True)
class DecisionView:
    """One log entry: what was decided, on what, and how it turned out."""

    id: int
    kind: DecisionKind
    reason: str | None
    # What was at stake when the call was made, in rupees per week.
    impact: float | None
    at: dt.datetime
    opportunity: OpportunitySummary
    experiment: ExperimentView | None


class DecisionService:
    def __init__(self, session: Session) -> None:
        self._decisions = DecisionRepository(session)
        self._analysis = AnalysisRepository(session)

    def find(self) -> list[DecisionView]:
        as_of = self._as_of()
        return [
            DecisionView(
                id=decision.id,
                kind=decision.kind,
                reason=decision.reason,
                impact=None if decision.impact is None else float(decision.impact),
                at=decision.created_at,
                opportunity=summary(opportunity),
                experiment=None if experiment is None else view(experiment, opportunity, as_of),
            )
            for decision, opportunity, experiment in self._decisions.list()
        ]

    def _as_of(self) -> dt.date | None:
        run = self._analysis.latest_run()
        return None if run is None else run.as_of_date
