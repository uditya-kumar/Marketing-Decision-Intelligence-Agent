"""The experiment plan and its verdict: targets, the measured window and all three answers."""

from __future__ import annotations

import datetime as dt

import pytest

from mdia.domain.experiments import (
    DEFAULT_DURATION_DAYS,
    MIN_EFFECT_PCT,
    MIN_SAMPLE_DAYS,
    improvement_pct,
    plan,
    progress,
    target,
    verdict,
    window,
)

pytestmark = pytest.mark.unit

APPROVED = dt.date(2026, 10, 14)


class TestTarget:
    def test_a_cost_metric_aims_at_the_lower_of_the_two_levels(self) -> None:
        assert target("cpa", baseline=610.0, reference=420.0) == 420.0

    def test_a_return_metric_aims_at_the_higher_of_the_two_levels(self) -> None:
        assert target("roas", baseline=2.4, reference=3.8) == 3.8

    def test_a_metric_with_no_direction_aims_at_where_it_was(self) -> None:
        assert target("spend", baseline=1000.0, reference=800.0) == 800.0

    def test_without_a_level_to_return_to_there_is_no_target(self) -> None:
        assert target("cpa", baseline=610.0, reference=None) is None


class TestPlan:
    def test_it_states_the_move_in_the_numbers_it_will_be_judged_on(self) -> None:
        filled = plan(
            "rotate_creative",
            "cpa",
            entity_name='Meta "Kurta Sale"',
            current=610.0,
            reference=420.0,
        )

        assert filled.action == "rotate_creative"
        assert filled.baseline == 610.0
        assert filled.target == 420.0
        assert filled.duration_days == DEFAULT_DURATION_DAYS
        assert filled.hypothesis == (
            'Rotating in a fresh creative on Meta "Kurta Sale" should move CPA'
            " from ₹610 to ₹420 within 7 days."
        )

    def test_with_nothing_to_aim_at_it_only_promises_an_improvement(self) -> None:
        filled = plan("fix_tracking", "cpa", entity_name="Meta", current=610.0, reference=None)

        assert filled.target is None
        assert "should improve CPA within 7 days." in filled.hypothesis


class TestWindow:
    def test_it_starts_the_day_after_approval_and_runs_the_duration(self) -> None:
        measured = window(APPROVED, DEFAULT_DURATION_DAYS)

        assert measured.start == dt.date(2026, 10, 15)
        assert measured.end == dt.date(2026, 10, 21)
        assert measured.days == DEFAULT_DURATION_DAYS


class TestImprovement:
    def test_a_falling_cost_is_an_improvement(self) -> None:
        assert improvement_pct("cpa", before=500.0, after=400.0) == pytest.approx(20.0)

    def test_a_falling_return_is_not(self) -> None:
        assert improvement_pct("roas", before=4.0, after=3.0) == pytest.approx(-25.0)

    def test_a_metric_with_no_direction_cannot_improve(self) -> None:
        assert improvement_pct("spend", before=100.0, after=200.0) is None


class TestVerdict:
    def test_a_big_enough_move_the_right_way_worked(self) -> None:
        found = verdict("cpa", before=610.0, after=420.0, sample_days=DEFAULT_DURATION_DAYS)

        assert found == "worked"

    def test_a_big_enough_move_the_wrong_way_did_not_work(self) -> None:
        found = verdict("cpa", before=420.0, after=610.0, sample_days=DEFAULT_DURATION_DAYS)

        assert found == "did_not_work"

    def test_a_move_inside_the_noise_is_inconclusive(self) -> None:
        after = 610.0 * (1 - (MIN_EFFECT_PCT - 1) / 100)

        assert verdict("cpa", before=610.0, after=after, sample_days=7) == "inconclusive"

    def test_too_few_days_is_inconclusive_however_good_it_looks(self) -> None:
        found = verdict("cpa", before=610.0, after=200.0, sample_days=MIN_SAMPLE_DAYS - 1)

        assert found == "inconclusive"

    def test_a_missing_reading_is_inconclusive_rather_than_a_guess(self) -> None:
        found = verdict("cpa", before=610.0, after=None, sample_days=DEFAULT_DURATION_DAYS)

        assert found == "inconclusive"


class TestProgress:
    def test_it_counts_the_days_elapsed_out_of_the_duration(self) -> None:
        measured = window(APPROVED, DEFAULT_DURATION_DAYS)
        seen = progress(started_on=APPROVED, ends_on=measured.end, as_of=dt.date(2026, 10, 18))

        assert (seen.day, seen.total, seen.due) == (4, 7, False)

    def test_it_is_due_once_the_data_reaches_the_last_day(self) -> None:
        measured = window(APPROVED, DEFAULT_DURATION_DAYS)
        seen = progress(started_on=APPROVED, ends_on=measured.end, as_of=measured.end)

        assert (seen.day, seen.total, seen.due) == (7, 7, True)
