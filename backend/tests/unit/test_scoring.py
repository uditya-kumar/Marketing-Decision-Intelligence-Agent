"""Scoring, the threshold, and the two reasons a signal is never shown."""

from __future__ import annotations

import datetime as dt
from dataclasses import replace

import pytest

from mdia.domain.periods import Period, trailing
from mdia.domain.scoring import MAX_CHANGE_PCT, is_suppressed, rank, rupee_impact, score
from mdia.domain.signals import WINDOW_DAYS, Entity, Signal, signal_id

pytestmark = pytest.mark.unit

AS_OF = dt.date(2026, 10, 28)
RECENT = trailing(AS_OF, WINDOW_DAYS)

META = Entity("channel", "meta_ads", "Meta Ads", channel="meta_ads")
GOOGLE = Entity("channel", "google_ads", "Google Ads", channel="google_ads")
ACCOUNT = Entity("account", "novawear", "NovaWear")


def signal(
    metric: str = "cpa",
    *,
    entity: Entity = META,
    current: float = 600,
    baseline: float = 400,
    detector: str = "baseline_change",
    window: Period = RECENT,
    **measures: float,
) -> Signal:
    change = (current - baseline) / abs(baseline) * 100
    return Signal(
        id=signal_id(detector, entity, metric, window),  # type: ignore[arg-type]
        detector=detector,  # type: ignore[arg-type]
        metric=metric,  # type: ignore[arg-type]
        entity=entity,
        window=window,
        current=current,
        baseline=baseline,
        change_pct=change,
        adverse=True,
        measures=measures,
    )


class TestRupeeImpact:
    def test_a_cpa_rise_costs_its_delta_per_conversion(self) -> None:
        assert rupee_impact(signal("cpa", platform_conversions=500)) == pytest.approx(100_000)

    def test_a_roas_slide_costs_revenue_on_the_spend_behind_it(self) -> None:
        hit = signal("roas", current=2.0, baseline=3.5, spend=300_000)

        assert rupee_impact(hit) == pytest.approx(450_000)

    def test_cpm_is_priced_per_thousand_impressions(self) -> None:
        hit = signal("cpm", current=250, baseline=200, impressions=1_000_000)

        assert rupee_impact(hit) == pytest.approx(50_000)

    def test_a_rate_puts_the_whole_spend_behind_it_at_stake(self) -> None:
        # CTR is not rupees, so the spend riding on it is what the move threatens;
        # how far it moved is the score's job, not the impact's.
        hit = signal("ctr", current=0.007, baseline=0.01, spend=200_000)

        assert rupee_impact(hit) == pytest.approx(200_000)

    def test_a_money_measure_is_a_daily_rate(self) -> None:
        hit = signal("spend", current=100_000, baseline=80_000)

        assert rupee_impact(hit) == pytest.approx(20_000 * WINDOW_DAYS)

    def test_nothing_at_stake_without_measures(self) -> None:
        assert rupee_impact(signal("ctr", current=0.007, baseline=0.01)) == 0.0


class TestScore:
    def test_score_is_the_change_times_the_impact(self) -> None:
        assert score(50, 100_000) == pytest.approx(50_000)
        assert score(-50, 100_000) == pytest.approx(50_000)
        assert score(None, 100_000) == 0.0

    def test_a_wild_percentage_is_capped(self) -> None:
        assert score(900, 100_000) == score(MAX_CHANGE_PCT, 100_000)

    def test_money_beats_drama(self) -> None:
        big_budget = signal("roas", current=2.8, baseline=3.5, spend=1_000_000)
        small_budget = signal("roas", entity=GOOGLE, current=1.0, baseline=3.5, spend=20_000)

        ranked = rank([small_budget, big_budget])

        assert [s.entity.id for s in ranked] == [big_budget.entity.id, small_budget.entity.id]


FESTIVE = [Period(dt.date(2026, 10, 20), dt.date(2026, 11, 5))]


class TestSuppression:
    def test_festive_windows_produce_no_performance_signals(self) -> None:
        during = signal("roas", current=2.0, baseline=3.5, spend=300_000)

        assert is_suppressed(during, festive=FESTIVE)
        assert rank([during], festive=FESTIVE) == []

    def test_a_signal_outside_the_festive_window_survives(self) -> None:
        before = signal(
            "roas",
            current=2.0,
            baseline=3.5,
            window=trailing(dt.date(2026, 10, 15), WINDOW_DAYS),
            spend=300_000,
        )

        assert not is_suppressed(before, festive=FESTIVE)
        assert len(rank([before], festive=FESTIVE)) == 1

    def test_a_broken_channel_produces_no_conversion_signals(self) -> None:
        meta = signal("cpa", platform_conversions=500)
        google = signal("cpa", entity=GOOGLE, platform_conversions=500)

        assert [s.entity.id for s in rank([meta, google], broken=["meta_ads"])] == [
            "channel:google_ads"
        ]

    def test_a_broken_channel_still_reports_its_click_metrics(self) -> None:
        # A pixel break cannot fake a CPC: impressions, clicks and spend keep arriving.
        cpc = signal("cpc", current=40.0, baseline=20.0, clicks=10_000)

        assert not is_suppressed(cpc, broken=["meta_ads"])
        assert len(rank([cpc], broken=["meta_ads"])) == 1

    def test_blended_platform_metrics_are_suppressed_too(self) -> None:
        blended = signal("roas", entity=ACCOUNT, current=2.0, baseline=3.5, spend=900_000)
        revenue = signal("store_revenue", entity=ACCOUNT, current=200_000, baseline=260_000)

        assert is_suppressed(blended, broken=["meta_ads"])
        assert not is_suppressed(revenue, broken=["meta_ads"])

    def test_the_tracking_break_itself_is_always_kept(self) -> None:
        break_signal = replace(
            signal("platform_conversions", current=0.16, baseline=1.0, detector="tracking_break"),
            impact=0.0,
        )

        assert not is_suppressed(break_signal, festive=FESTIVE, broken=["meta_ads"])
        assert len(rank([break_signal], festive=FESTIVE, broken=["meta_ads"])) == 1


class TestThreshold:
    def test_pocket_change_is_dropped_and_real_money_kept(self) -> None:
        small = signal("cpa", current=410, baseline=400, platform_conversions=12)
        large = signal("cpa", platform_conversions=500)

        ranked = rank([small, large], min_score=5_000)

        assert len(ranked) == 1
        assert ranked[0].impact == pytest.approx(100_000)
        assert ranked[0].score == pytest.approx(50_000)
