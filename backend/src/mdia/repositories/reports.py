"""Stored weekly reports (FR-11.3): save one week, list the history, read one back."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from mdia.models import WeeklyReport

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Sequence

    from sqlalchemy.orm import Session

# Long enough to be a history, short enough to stay one query.
LIST_LIMIT = 52


class ReportRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, row: dict[str, Any]) -> WeeklyReport:
        """Store the week, replacing an earlier report for the same week end."""
        stmt = (
            insert(WeeklyReport)
            .values(**row)
            .on_conflict_do_update(
                index_elements=[WeeklyReport.week_end],
                set_={key: value for key, value in row.items() if key != "week_end"},
            )
            .returning(WeeklyReport)
        )
        return self._session.execute(stmt).scalar_one()

    def list(self, limit: int = LIST_LIMIT) -> Sequence[WeeklyReport]:
        stmt = select(WeeklyReport).order_by(WeeklyReport.week_end.desc()).limit(limit)
        return list(self._session.execute(stmt).scalars())

    def get(self, report_id: int) -> WeeklyReport | None:
        return self._session.get(WeeklyReport, report_id)

    def for_week(self, week_end: dt.date) -> WeeklyReport | None:
        stmt = select(WeeklyReport).where(WeeklyReport.week_end == week_end)
        return self._session.execute(stmt).scalar_one_or_none()
