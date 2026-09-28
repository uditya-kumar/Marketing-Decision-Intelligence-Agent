"""Goals: break-even ROAS, goal status and pro-rated targets."""

from __future__ import annotations

import pytest

from mdia.domain.goals import break_even_roas, goal_status, is_profitable_roas, prorated_target

pytestmark = pytest.mark.unit


def test_break_even_roas_is_one_over_margin() -> None:
    assert break_even_roas(40) == pytest.approx(2.5)
    assert break_even_roas(100) == 1


@pytest.mark.parametrize("margin", [0, -5, 101])
def test_break_even_roas_rejects_impossible_margins(margin: float) -> None:
    with pytest.raises(ValueError, match="gross margin"):
        break_even_roas(margin)


@pytest.mark.parametrize(
    ("actual", "status"),
    [(3.9, "ahead"), (3.6, "on_track"), (3.4, "on_track"), (3.2, "behind")],
)
def test_higher_is_better_status_against_target(actual: float, status: str) -> None:
    assert goal_status(actual, 3.5) == status


@pytest.mark.parametrize(
    ("cpa", "status"),
    [(428, "ahead"), (500, "on_track"), (520, "on_track"), (610, "behind"), (0, "ahead")],
)
def test_for_cost_metrics_lower_is_better(cpa: float, status: str) -> None:
    assert goal_status(cpa, 500, higher_is_better=False) == status


def test_goal_status_needs_a_positive_target() -> None:
    with pytest.raises(ValueError, match="target"):
        goal_status(10, 0)


def test_prorated_target_scales_with_days_elapsed() -> None:
    assert prorated_target(31_00_000, 14, 31) == pytest.approx(14_00_000)
    assert prorated_target(30_00_000, 0, 30) == 0
    with pytest.raises(ValueError, match="within the month"):
        prorated_target(1, 31, 30)


def test_a_roas_is_profitable_only_above_break_even() -> None:
    assert is_profitable_roas(3.5, gross_margin_pct=40)  # break-even 2.5×
    assert not is_profitable_roas(2.5, gross_margin_pct=40)
    assert not is_profitable_roas(1.5, gross_margin_pct=40)
