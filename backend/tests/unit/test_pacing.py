"""Budget pacing: run-rate projection, status and the suggested daily spend."""

from __future__ import annotations

import datetime as dt

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mdia.domain.pacing import pace, pacing_status
from mdia.domain.periods import days_in_month

pytestmark = pytest.mark.unit

D = dt.date


def test_spend_on_plan_is_on_track() -> None:
    pacing = pace(310_000, 100_000, D(2026, 10, 10))

    assert pacing.status == "on_track"
    assert pacing.daily_run_rate == pytest.approx(10_000)
    assert pacing.projected == pytest.approx(310_000)
    assert pacing.month_elapsed_pct == pytest.approx(10 / 31 * 100)
    assert pacing.suggested_daily == pytest.approx(210_000 / 21)
    assert pacing.remaining_budget == pytest.approx(210_000)


def test_overspending_is_over_and_suggests_slowing_down() -> None:
    # The demo storyline: Meta spending well above its October plan.
    pacing = pace(800_000, 442_606, D(2026, 10, 14))

    assert pacing.status == "over"
    assert pacing.spent_pct == pytest.approx(55.3, abs=0.1)
    assert pacing.suggested_daily is not None
    assert pacing.suggested_daily < pacing.daily_run_rate


def test_underspending_is_under() -> None:
    assert pace(300_000, 50_000, D(2026, 9, 15)).status == "under"


def test_tolerance_band_edges() -> None:
    assert pacing_status(110, 100) == "on_track"
    assert pacing_status(110.01, 100) == "over"
    assert pacing_status(90, 100) == "on_track"
    assert pacing_status(89.99, 100) == "under"


def test_first_day_projects_the_month_from_one_day() -> None:
    pacing = pace(300_000, 10_000, D(2026, 9, 1))

    assert pacing.projected == pytest.approx(300_000)
    assert pacing.suggested_daily == pytest.approx(290_000 / 29)


def test_last_day_has_nothing_left_to_suggest() -> None:
    pacing = pace(310_000, 320_000, D(2026, 10, 31))

    assert pacing.projected == pytest.approx(320_000)
    assert pacing.month_elapsed_pct == pytest.approx(100)
    assert pacing.suggested_daily is None


def test_budget_already_spent_suggests_zero() -> None:
    pacing = pace(100_000, 120_000, D(2026, 10, 20))

    assert pacing.suggested_daily == 0
    assert pacing.remaining_budget == pytest.approx(-20_000)
    assert pacing.spent_pct == pytest.approx(120)


@pytest.mark.parametrize(
    ("day", "days"),
    [(D(2028, 2, 10), 29), (D(2026, 2, 10), 28), (D(2026, 9, 10), 30), (D(2026, 10, 10), 31)],
)
def test_projection_uses_the_months_real_length(day: dt.date, days: int) -> None:
    assert pace(100_000, 10_000, day).projected == pytest.approx(1_000 * days)


def test_invalid_inputs_are_rejected() -> None:
    with pytest.raises(ValueError, match="budget"):
        pace(0, 100, D(2026, 10, 10))
    with pytest.raises(ValueError, match="spend"):
        pace(100, -1, D(2026, 10, 10))


@given(
    budget=st.floats(1, 1e8, allow_subnormal=False),
    spent=st.floats(0, 1e8, allow_subnormal=False),
    day=st.dates(D(2020, 1, 1), D(2030, 12, 31)),
)
def test_suggested_spend_lands_on_budget(budget: float, spent: float, day: dt.date) -> None:
    pacing = pace(budget, spent, day)
    remaining = days_in_month(day) - day.day

    # Projecting the run rate forward can never land under what is already spent, give or
    # take the last bits of a division that dividing by the days and multiplying back loses.
    assert pacing.projected >= spent or pacing.projected == pytest.approx(spent)
    if pacing.suggested_daily is None:
        assert remaining == 0
    elif spent <= budget:
        assert spent + pacing.suggested_daily * remaining == pytest.approx(budget)
