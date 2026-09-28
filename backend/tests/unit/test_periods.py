"""Date windows used for "vs last period" comparisons."""

from __future__ import annotations

import datetime as dt

import pytest

from mdia.domain.periods import Period, days_in_month, month_to_date, trailing

pytestmark = pytest.mark.unit

D = dt.date


def test_trailing_week_and_the_week_before() -> None:
    week = trailing(D(2026, 10, 14), 7)
    assert week == Period(D(2026, 10, 8), D(2026, 10, 14))
    assert week.days == 7
    assert week.previous() == Period(D(2026, 10, 1), D(2026, 10, 7))


def test_dates_are_inclusive_and_ordered() -> None:
    period = Period(D(2026, 2, 27), D(2026, 3, 2))
    assert period.dates() == [D(2026, 2, 27), D(2026, 2, 28), D(2026, 3, 1), D(2026, 3, 2)]
    assert D(2026, 3, 2) in period
    assert D(2026, 3, 3) not in period


def test_month_to_date_and_month_length() -> None:
    assert month_to_date(D(2026, 10, 14)) == Period(D(2026, 10, 1), D(2026, 10, 14))
    assert days_in_month(D(2026, 2, 10)) == 28
    assert days_in_month(D(2028, 2, 10)) == 29


def test_invalid_periods_are_rejected() -> None:
    with pytest.raises(ValueError, match="end on or after"):
        Period(D(2026, 10, 2), D(2026, 10, 1))
    with pytest.raises(ValueError, match="at least one day"):
        trailing(D(2026, 10, 1), 0)
