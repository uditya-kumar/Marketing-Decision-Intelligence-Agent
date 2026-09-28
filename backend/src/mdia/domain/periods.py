"""Date windows: trailing periods, the period before them, and month-to-date."""

from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Period:
    """Inclusive date range."""

    start: dt.date
    end: dt.date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("a period must end on or after its start")

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def dates(self) -> list[dt.date]:
        return [self.start + dt.timedelta(days=i) for i in range(self.days)]

    def previous(self) -> Period:
        """The equally long period just before this one, for "vs last period"."""
        end = self.start - dt.timedelta(days=1)
        return Period(end - dt.timedelta(days=self.days - 1), end)

    def __contains__(self, day: object) -> bool:
        return isinstance(day, dt.date) and self.start <= day <= self.end

    def overlaps(self, other: Period) -> bool:
        return self.start <= other.end and other.start <= self.end


def trailing(end: dt.date, days: int) -> Period:
    """The ``days`` days ending on (and including) ``end``."""
    if days < 1:
        raise ValueError("a period needs at least one day")
    return Period(end - dt.timedelta(days=days - 1), end)


def month_to_date(day: dt.date) -> Period:
    return Period(day.replace(day=1), day)


def days_in_month(day: dt.date) -> int:
    return calendar.monthrange(day.year, day.month)[1]
