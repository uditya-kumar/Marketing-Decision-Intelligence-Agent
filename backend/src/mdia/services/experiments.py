"""Experiments (FR-10): draft one from a recommendation, decide on it, then judge it.

The service moves rows between statuses and fetches the numbers; every judgement — the
target, the verdict, the progress — comes from ``domain/experiments.py``. Approving,
rejecting and dismissing all write to the decision log, which is what makes the chain in
FR-10.4 readable afterwards.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from mdia.core.errors import NotFoundError, ValidationError
from mdia.domain.experiments import verdict, window
from mdia.domain.signals import Window
from mdia.repositories.analysis import AnalysisRepository
from mdia.repositories.decisions import DecisionRepository
from mdia.repositories.experiments import ExperimentRepository
from mdia.repositories.metrics import MetricsRepository
from mdia.services.experiment_rows import (
    ExperimentsToday,
    ExperimentView,
    draft_row,
    group_today,
    view,
)

if TYPE_CHECKING:
    import datetime as dt

    from sqlalchemy.orm import Session

    from mdia.domain.kpi import Metric
    from mdia.domain.periods import Period
    from mdia.models import Experiment, Opportunity
    from mdia.models.experiments import DecisionKind


@dataclass(frozen=True, slots=True)
class Reading:
    """A metric over one window, and how many days of data were behind it."""

    value: float | None
    days: int


class ExperimentService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._experiments = ExperimentRepository(session)
        self._decisions = DecisionRepository(session)
        self._analysis = AnalysisRepository(session)
        self._metrics = MetricsRepository(session)

    def find(self) -> list[ExperimentView]:
        as_of = self._as_of()
        return [view(row, found, as_of) for row, found in self._experiments.list()]

    def today(self) -> ExperimentsToday:
        """The Today screen's one-line summary of what is under way."""
        return group_today(self.find())

    def get(self, experiment_id: int) -> ExperimentView:
        row, opportunity = self._require(experiment_id)
        return view(row, opportunity, self._as_of())

    def draft(self, opportunity_id: int) -> ExperimentView:
        """Auto-fill an experiment from the stored recommendation (FR-10.1).

        Asking twice returns the same draft: an opportunity only ever has one change
        under test, and the numbers behind it do not move until the next analysis run.
        """
        opportunity = self._opportunity(opportunity_id)
        existing = self._experiments.live_for(opportunity_id)
        if existing is not None:
            return view(existing, opportunity, self._as_of())
        row = self._experiments.create(draft_row(opportunity))
        self._session.commit()
        return view(row, opportunity, self._as_of())

    def approve(self, experiment_id: int, reason: str | None = None) -> ExperimentView:
        """Start the clock: the team makes the change, MDIA watches the metric (FR-10.2)."""
        row, opportunity = self._require_draft(experiment_id)
        as_of = self._as_of()
        if as_of is None:
            raise ValidationError("There is no data yet to measure a change against.")
        self._experiments.set_status(
            row.id,
            "running",
            started_on=as_of,
            ends_on=window(as_of, row.duration_days).end,
            reason=reason,
        )
        self._analysis.set_status(opportunity.id, "experimenting")
        self._decide("approve", opportunity, row.id, reason)
        return self.get(experiment_id)

    def reject(self, experiment_id: int, reason: str | None = None) -> ExperimentView:
        """Turn the change down; the opportunity stays open for another answer."""
        row, opportunity = self._require_draft(experiment_id)
        self._experiments.set_status(row.id, "rejected", reason=reason)
        self._decide("reject", opportunity, row.id, reason)
        return self.get(experiment_id)

    def evaluate_due(self, as_of: dt.date, run_id: int) -> list[int]:
        """Judge every running experiment the data now covers, returning the ids judged.

        The analysis run calls this after storing its opportunities (FR-10.3), so closing
        the loop needs nothing from the user but next week's exports.
        """
        judged = []
        for row, opportunity in self._experiments.due(as_of):
            self._evaluate(row, opportunity, run_id)
            judged.append(row.id)
        return judged

    def _evaluate(self, row: Experiment, opportunity: Opportunity, run_id: int) -> None:
        metric = cast("Metric", row.metric)
        measured = window(cast("dt.date", row.started_on), row.duration_days)
        after = self._reading(metric, measured, opportunity)
        before = self._reading(metric, measured.previous(), opportunity)
        found = verdict(metric, before=before.value, after=after.value, sample_days=after.days)
        self._experiments.set_status(
            row.id,
            "completed",
            before_value=before.value,
            after_value=after.value,
            sample_days=after.days,
            verdict=found,
            evaluated_on=row.ends_on,
        )
        # A change that worked closes the opportunity; so does one that did not, if this
        # run no longer detects the problem. Otherwise it goes back on the list.
        still_there = found != "worked" and opportunity.analysis_run_id == run_id
        self._analysis.set_status(opportunity.id, "open" if still_there else "resolved")

    def _reading(self, metric: Metric, period: Period, opportunity: Opportunity) -> Reading:
        totals = self._metrics.entity_totals(
            period, opportunity.entity_level, opportunity.entity_key
        )
        return Reading(Window(period, totals.measures).value(metric), totals.days)

    def _decide(
        self, kind: DecisionKind, opportunity: Opportunity, experiment_id: int, reason: str | None
    ) -> None:
        self._decisions.log(
            kind,
            opportunity_id=opportunity.id,
            experiment_id=experiment_id,
            reason=reason,
            impact=opportunity.impact,
        )
        self._session.commit()

    def _require(self, experiment_id: int) -> tuple[Experiment, Opportunity]:
        row = self._experiments.get(experiment_id)
        if row is None:
            raise NotFoundError(f"No experiment {experiment_id}.")
        return row, self._opportunity(row.opportunity_id)

    def _require_draft(self, experiment_id: int) -> tuple[Experiment, Opportunity]:
        """A decision can only be made once, and only before the change has started."""
        row, opportunity = self._require(experiment_id)
        if row.status != "draft":
            raise ValidationError("This experiment has already been decided on.")
        return row, opportunity

    def _opportunity(self, opportunity_id: int) -> Opportunity:
        row = self._analysis.get(opportunity_id)
        if row is None:
            raise NotFoundError(f"No opportunity {opportunity_id}.")
        return row

    def _as_of(self) -> dt.date | None:
        """The last day of data, which is the clock an experiment runs on."""
        run = self._analysis.latest_run()
        return None if run is None else run.as_of_date
