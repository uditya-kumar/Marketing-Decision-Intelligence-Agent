"""Analysis runs and opportunity rows: writes only, plus the queries the API needs."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select, update

from mdia.models import AnalysisRun, Opportunity
from mdia.repositories.upsert import upsert

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from sqlalchemy.orm import Session

    from mdia.models.analysis import AnalysisStatus, OpportunityStatus

# A run that never wrote its result (the process died) shouldn't block the next one.
STALE_RUN_MINUTES = 15


class AnalysisRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def start(self, as_of: dt.date) -> AnalysisRun:
        run = AnalysisRun(status="running", as_of_date=as_of)
        self._session.add(run)
        self._session.flush()
        return run

    def finish(
        self,
        run_id: int,
        *,
        status: AnalysisStatus,
        signals: int = 0,
        opportunities: int = 0,
        llm: int = 0,
        error: str | None = None,
    ) -> None:
        self._session.execute(
            update(AnalysisRun)
            .where(AnalysisRun.id == run_id)
            .values(
                status=status,
                signal_count=signals,
                opportunity_count=opportunities,
                llm_count=llm,
                error=error,
                finished_at=func.now(),
            )
        )

    def latest_run(self) -> AnalysisRun | None:
        stmt = select(AnalysisRun).order_by(AnalysisRun.id.desc()).limit(1)
        return self._session.scalars(stmt).first()

    def is_running(self) -> bool:
        """Whether a run is in flight, ignoring one that died without reporting."""
        cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(minutes=STALE_RUN_MINUTES)
        stmt = (
            select(AnalysisRun.id)
            .where(AnalysisRun.status == "running", AnalysisRun.started_at > cutoff)
            .limit(1)
        )
        return self._session.scalars(stmt).first() is not None

    def seen_dates(self, keys: Collection[str]) -> dict[str, tuple[dt.date, dt.date]]:
        """When each of ``keys`` was first and last detected, for the rows that exist."""
        if not keys:
            return {}
        stmt = select(
            Opportunity.key, Opportunity.first_seen_date, Opportunity.last_seen_date
        ).where(Opportunity.key.in_(keys))
        return {key: (first, last) for key, first, last in self._session.execute(stmt)}

    def save(self, run_id: int, rows: Sequence[dict[str, Any]]) -> None:
        """Write this run's opportunities, then retire the ones it no longer finds.

        The upsert leaves ``status`` alone so a dismissal survives a re-run; a problem
        that had been resolved and is back reopens, and anything missing from this run
        is resolved.
        """
        if rows:
            upsert(self._session, Opportunity, rows, key=["key"])
            self._session.execute(
                update(Opportunity)
                .where(Opportunity.analysis_run_id == run_id, Opportunity.status == "resolved")
                .values(status="open")
            )
        self._session.execute(
            update(Opportunity)
            .where(Opportunity.status == "open", Opportunity.analysis_run_id != run_id)
            .values(status="resolved")
        )

    def list(
        self,
        status: Collection[OpportunityStatus] | None = None,
        kind: str | None = None,
        limit: int = 100,
    ) -> Sequence[Opportunity]:
        """Opportunities, most urgent first; a row the LLM never reached has no priority."""
        stmt = (
            select(Opportunity)
            .order_by(Opportunity.priority.desc().nullslast(), Opportunity.score.desc())
            .limit(limit)
        )
        if status:
            stmt = stmt.where(Opportunity.status.in_(status))
        if kind:
            stmt = stmt.where(Opportunity.kind == kind)
        return self._session.scalars(stmt).all()

    def get(self, opportunity_id: int) -> Opportunity | None:
        return self._session.get(Opportunity, opportunity_id)

    def set_status(self, opportunity_id: int, status: OpportunityStatus) -> None:
        """Move one opportunity's status, as an experiment starting or ending does."""
        self._session.execute(
            update(Opportunity).where(Opportunity.id == opportunity_id).values(status=status)
        )

    def dismiss(self, opportunity_id: int, reason: str) -> None:
        self._session.execute(
            update(Opportunity)
            .where(Opportunity.id == opportunity_id)
            .values(status="dismissed", dismissed_reason=reason)
        )
