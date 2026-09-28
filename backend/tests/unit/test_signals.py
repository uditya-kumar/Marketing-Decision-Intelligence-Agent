"""Detectors: each one fires on a real movement and stays quiet otherwise."""

from __future__ import annotations

import datetime as dt

import pytest

from mdia.domain.periods import Period, trailing
from mdia.domain.signals import (
    BASELINE_DAYS,
    WINDOW_DAYS,
    Entity,
    Window,
    baseline_change,
    enough_sample,
    funnel_drop,
    goal_breach,
    segment_divergence,
    signal_id,
    tracking_break,
)
from mdia.domain.trust import TrackingCheck

pytestmark = pytest.mark.unit

AS_OF = dt.date(2026, 10, 28)
RECENT = trailing(AS_OF, WINDOW_DAYS)
HISTORY = trailing(RECENT.start - dt.timedelta(days=1), BASELINE_DAYS)

CHANNEL = Entity("channel", "meta_ads", "Meta Ads", channel="meta_ads")
SEGMENT = Entity(
    "age_group",
    "31:25-34",
    "25-34",
    channel="meta_ads",
    ancestors=("channel:meta_ads", "ad_set:31"),
)


def recent(**measures: float) -> Window:
    return Window(RECENT, measures)


def history(**measures: float) -> Window:
    return Window(HISTORY, measures)


class TestBaselineChange:
    def test_a_cpa_rise_is_an_adverse_signal(self) -> None:
        signal = baseline_change(
            CHANNEL,
            "cpa",
            recent(spend=300_000, platform_conversions=500),
            history(spend=1_200_000, platform_conversions=3_000),
        )

        assert signal is not None
        assert signal.detector == "baseline_change"
        assert signal.current == pytest.approx(600)
        assert signal.baseline == pytest.approx(400)
        assert signal.change_pct == pytest.approx(50)
        assert signal.adverse
        assert signal.window == RECENT

    def test_a_roas_rise_is_a_win_not_a_problem(self) -> None:
        signal = baseline_change(
            CHANNEL,
            "roas",
            recent(platform_revenue=900_000, spend=300_000, platform_conversions=500),
            history(platform_revenue=2_400_000, spend=1_200_000, platform_conversions=3_000),
        )

        assert signal is not None
        assert signal.adverse is False

    def test_small_movement_is_noise(self) -> None:
        assert (
            baseline_change(
                CHANNEL,
                "cpa",
                recent(spend=208_000, platform_conversions=500),
                history(spend=1_200_000, platform_conversions=3_000),
            )
            is None
        )

    def test_too_few_conversions_to_judge_cpa(self) -> None:
        assert (
            baseline_change(
                CHANNEL,
                "cpa",
                recent(spend=3_000, platform_conversions=4),
                history(spend=4_000, platform_conversions=20),
            )
            is None
        )

    def test_a_measure_is_compared_per_day(self) -> None:
        signal = baseline_change(CHANNEL, "spend", recent(spend=700_000), history(spend=2_240_000))

        assert signal is not None
        assert signal.current == pytest.approx(100_000)
        assert signal.baseline == pytest.approx(80_000)
        # Spend is neither good nor bad on its own.
        assert signal.adverse is False


class TestGoalBreach:
    def test_roas_below_target_breaches(self) -> None:
        signal = goal_breach(
            CHANNEL,
            "roas",
            recent(platform_revenue=600_000, spend=300_000, platform_conversions=500),
            3.5,
        )

        assert signal is not None
        assert signal.detector == "goal_breach"
        assert signal.baseline == pytest.approx(3.5)
        assert signal.current == pytest.approx(2.0)
        assert signal.change_pct == pytest.approx(-42.857, abs=1e-3)
        assert signal.adverse

    def test_roas_at_target_does_not(self) -> None:
        assert (
            goal_breach(
                CHANNEL,
                "roas",
                recent(platform_revenue=1_080_000, spend=300_000, platform_conversions=500),
                3.5,
            )
            is None
        )

    def test_overspend_breaches_a_daily_budget(self) -> None:
        signal = goal_breach(CHANNEL, "spend", recent(spend=700_000), 80_000, prefer_higher=False)

        assert signal is not None
        assert signal.current == pytest.approx(100_000)

    def test_spend_within_the_daily_budget_does_not(self) -> None:
        assert (
            goal_breach(CHANNEL, "spend", recent(spend=560_000), 80_000, prefer_higher=False)
            is None
        )


class TestFunnelDrop:
    def test_add_to_cart_collapse_is_reported(self) -> None:
        signals = funnel_drop(
            CHANNEL,
            recent(sessions=10_000, add_to_cart=300, checkout=150, purchases=60),
            history(sessions=40_000, add_to_cart=2_000, checkout=1_000, purchases=400),
        )

        assert [s.metric for s in signals] == ["atc_rate"]
        assert signals[0].detector == "funnel_drop"
        assert signals[0].change_pct == pytest.approx(-40)

    def test_a_steady_funnel_reports_nothing(self) -> None:
        assert (
            funnel_drop(
                CHANNEL,
                recent(sessions=10_000, add_to_cart=500, checkout=250, purchases=100),
                history(sessions=40_000, add_to_cart=2_000, checkout=1_000, purchases=400),
            )
            == []
        )

    def test_an_improving_funnel_is_not_a_drop(self) -> None:
        assert (
            funnel_drop(
                CHANNEL,
                recent(sessions=10_000, add_to_cart=800, checkout=400, purchases=160),
                history(sessions=40_000, add_to_cart=2_000, checkout=1_000, purchases=400),
            )
            == []
        )


class TestSegmentDivergence:
    def test_an_age_group_far_worse_than_its_peers(self) -> None:
        signal = segment_divergence(
            SEGMENT,
            "cpa",
            Window(RECENT, {"spend": 80_000, "platform_conversions": 100}),
            Window(RECENT, {"spend": 240_000, "platform_conversions": 600}),
        )

        assert signal is not None
        assert signal.detector == "segment_divergence"
        assert signal.current == pytest.approx(800)
        assert signal.baseline == pytest.approx(400)
        assert signal.adverse

    def test_a_segment_close_to_its_peers(self) -> None:
        assert (
            segment_divergence(
                SEGMENT,
                "cpa",
                Window(RECENT, {"spend": 42_000, "platform_conversions": 100}),
                Window(RECENT, {"spend": 240_000, "platform_conversions": 600}),
            )
            is None
        )


class TestTrackingBreak:
    def test_a_broken_pixel_becomes_a_signal(self) -> None:
        check = TrackingCheck("broken", 0.16, dt.date(2026, 10, 24), -81.2, -10.2)
        signal = tracking_break(CHANNEL, check, recent(spend=300_000))

        assert signal is not None
        assert signal.detector == "tracking_break"
        assert signal.metric == "platform_conversions"
        assert signal.baseline == pytest.approx(1.0)
        assert signal.change_pct == pytest.approx(-84)

    def test_healthy_tracking_is_silent(self) -> None:
        check = TrackingCheck("ok", 0.98, None, -1.2, -0.4)

        assert tracking_break(CHANNEL, check, recent(spend=300_000)) is None


def test_sample_guard_asks_both_sides_of_the_ratio() -> None:
    assert enough_sample("cpa", recent(spend=5_000, platform_conversions=30))
    assert not enough_sample("cpa", recent(spend=5_000, platform_conversions=29))
    assert enough_sample("ctr", recent(impressions=5_000, clicks=100))
    assert not enough_sample("ctr", recent(impressions=4_999, clicks=100))


def test_revenue_is_judged_on_the_sales_behind_it() -> None:
    # Rupees have no sample size of their own; the purchases that earned them do.
    assert enough_sample(
        "roas", recent(platform_revenue=900_000, spend=5_000, platform_conversions=30)
    )
    assert not enough_sample(
        "roas", recent(platform_revenue=900_000, spend=5_000, platform_conversions=3)
    )
    assert enough_sample("store_revenue", recent(store_revenue=900_000, store_orders=30))
    assert not enough_sample("store_revenue", recent(store_revenue=900_000, store_orders=29))


def test_signal_ids_are_stable_per_entity_metric_and_window() -> None:
    assert (
        signal_id("baseline_change", CHANNEL, "cpa", RECENT) == "chg|channel:meta_ads|cpa|20261028"
    )
    assert signal_id("baseline_change", CHANNEL, "cpa", RECENT) == signal_id(
        "baseline_change", CHANNEL, "cpa", trailing(AS_OF, WINDOW_DAYS)
    )
    assert signal_id("baseline_change", CHANNEL, "cpa", RECENT) != signal_id(
        "baseline_change", CHANNEL, "cpa", Period(RECENT.start, AS_OF - dt.timedelta(days=1))
    )
