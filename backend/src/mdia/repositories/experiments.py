"""Experiment rows: create one, move it through its statuses, find the ones now due."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select, update

from mdia.models import Experiment, Opportunity

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Sequence

    from sqlalchemy import Select
    from sqlalchemy.orm import Session

    from mdia.models.experiments import ExperimentStatus

# Statuses that still refer to a change nobody has finished with.
LIVE: tuple[ExperimentStatus, ...] = ("draft", "running")

type Pair = tuple[Experiment, Opportunity]


class ExperimentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, values: dict[str, Any]) -> Experiment:
        experiment = Experiment(**values)
        self._session.add(experiment)
        self._session.flush()
        return experiment

    def get(self, experiment_id: int) -> Experiment | None:
        return self._session.get(Experiment, experiment_id)

    def live_for(self, opportunity_id: int) -> Experiment | None:
        """The draft or running experiment on this opportunity, so one is never duplicated."""
        stmt = (
            select(Experiment)
            .where(Experiment.opportunity_id == opportunity_id, Experiment.status.in_(LIVE))
            .order_by(Experiment.id.desc())
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def list(self, limit: int = 100) -> Sequence[Pair]:
        """Every experiment with the opportunity it came from, newest first."""
        return self._pairs(self._joined().order_by(Experiment.id.desc()).limit(limit))

    def due(self, as_of: dt.date) -> Sequence[Pair]:
        """Running experiments whose window the data now covers (FR-10.3)."""
        stmt = self._joined().where(Experiment.status == "running", Experiment.ends_on <= as_of)
        return self._pairs(stmt.order_by(Experiment.id))

    def set_status(self, experiment_id: int, status: ExperimentStatus, **values: Any) -> None:
        self._session.execute(
            update(Experiment).where(Experiment.id == experiment_id).values(status=status, **values)
        )

    def _joined(self) -> Select[Experiment, Opportunity]:
        return select(Experiment, Opportunity).join(
            Opportunity, Opportunity.id == Experiment.opportunity_id
        )

    def _pairs(self, stmt: Select[Experiment, Opportunity]) -> Sequence[Pair]:
        return [
            (experiment, opportunity) for experiment, opportunity in self._session.execute(stmt)
        ]
