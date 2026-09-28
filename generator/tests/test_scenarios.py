"""Each scenario leaves its expected fingerprint relative to the no-scenario counterfactual.

Common random numbers make this exact: anything a scenario does not touch is bit-identical.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

import numpy as np

from helpers import slots_where, total

if TYPE_CHECKING:
    from conftest import RunEvent
    from novawear_sim.engine import Simulation

START = date(2026, 2, 2)


def ratio(
    sim: Simulation, num: np.ndarray, den: np.ndarray, a: date, b: date, slots: np.ndarray
) -> float:
    return total(num, sim, a, b, slots) / total(den, sim, a, b, slots)


def day(n: int) -> date:
    return START + timedelta(days=n)


def test_creative_fatigue_raises_frequency_and_decays_ctr(
    baseline: Simulation, run_event: RunEvent
) -> None:
    sim = run_event("creative_fatigue", START, 12, {"creative": "ig_reels_young_c1"})
    slots = slots_where(baseline, creative="ig_reels_young_c1")
    a, b = day(6), day(11)

    def kpis(s: Simulation) -> tuple[float, float, float]:
        d = s.delivery
        return (
            ratio(s, d.impressions, d.reach, a, b, slots),
            ratio(s, d.clicks, d.impressions, a, b, slots),
            ratio(s, d.spend, d.clicks, a, b, slots),
        )

    (base_freq, base_ctr, base_cpc), (freq, ctr, cpc) = kpis(baseline), kpis(sim)
    assert freq > 1.25 * base_freq
    assert ctr < 0.8 * base_ctr
    assert cpc > 1.2 * base_cpc
    # After the window the creative is rotated: fatigue wears off within a few weeks.
    c = sim.world.index_of("creative", "ig_reels_young_c1")
    later = sim.timeline.mask(day(35), day(40))
    assert sim.delivery.fatigue[later, c].min() > 0.97


def test_audience_mismatch_shifts_delivery_to_a_low_intent_segment(
    baseline: Simulation, run_event: RunEvent
) -> None:
    sim = run_event("audience_mismatch", START, 8, {"ad_set": "fb_women_metro"})
    ad_set = slots_where(baseline, ad_set="fb_women_metro")
    young = ad_set & slots_where(baseline, age_group="18-24")
    a, b = day(2), day(7)

    def share(s: Simulation) -> float:
        return total(s.delivery.spend, s, a, b, young) / total(s.delivery.spend, s, a, b, ad_set)

    def cvr(s: Simulation, slots: np.ndarray) -> float:
        return ratio(s, s.paid.funnel.purchases, s.delivery.clicks, a, b, slots)

    assert share(sim) > 2 * share(baseline)
    assert cvr(sim, ad_set) < 0.9 * cvr(baseline, ad_set)
    assert cvr(sim, young) < 0.5 * cvr(baseline, young)
    # Total ad-set spend is unchanged — only its mix moved.
    assert np.isclose(
        total(sim.delivery.spend, sim, a, b, ad_set),
        total(baseline.delivery.spend, baseline, a, b, ad_set),
        rtol=0.05,
    )


def test_landing_page_break_hits_engagement_on_one_device_only(
    baseline: Simulation, run_event: RunEvent
) -> None:
    sim = run_event("landing_page_break", START, 4, {"channel": "meta_ads"})
    mobile = slots_where(baseline, channel="meta_ads", device="mobile")
    desktop = slots_where(baseline, channel="meta_ads", device="desktop")
    a, b = START, day(3)

    def engage(s: Simulation) -> float:
        f = s.paid.funnel
        return ratio(s, f.engaged, f.sessions, a, b, mobile)

    assert engage(sim) < 0.5 * engage(baseline)
    np.testing.assert_array_equal(sim.delivery.clicks, baseline.delivery.clicks)
    np.testing.assert_array_equal(
        sim.paid.funnel.engaged[:, desktop], baseline.paid.funnel.engaged[:, desktop]
    )
    assert total(sim.paid.funnel.purchases, sim, a, b, mobile) < 0.6 * total(
        baseline.paid.funnel.purchases, baseline, a, b, mobile
    )


def test_cpc_spike_raises_cost_per_click_at_constant_spend(
    baseline: Simulation, run_event: RunEvent
) -> None:
    sim = run_event("cpc_spike", START, 6, {"channel": "google_ads"})
    slots = slots_where(baseline, channel="google_ads")
    a, b = day(1), day(5)
    d0, d1 = baseline.delivery, sim.delivery
    assert ratio(sim, d1.spend, d1.clicks, a, b, slots) > 1.4 * ratio(
        baseline, d0.spend, d0.clicks, a, b, slots
    )
    np.testing.assert_array_equal(d1.spend, d0.spend)
    assert total(sim.paid.funnel.purchases, sim, a, b, slots) < 0.8 * total(
        baseline.paid.funnel.purchases, baseline, a, b, slots
    )


def test_channel_opportunity_lifts_roas_at_the_same_spend(
    baseline: Simulation, run_event: RunEvent
) -> None:
    sim = run_event("channel_opportunity", START, 10, {"channel": "google_ads"})
    slots = slots_where(baseline, channel="google_ads")
    a, b = day(3), day(9)

    def roas(s: Simulation) -> float:
        return ratio(s, s.paid.funnel.revenue, s.delivery.spend, a, b, slots)

    assert roas(sim) > 1.2 * roas(baseline)
    np.testing.assert_array_equal(sim.delivery.spend, baseline.delivery.spend)


def test_campaign_opportunity_leaves_sibling_campaigns_alone(
    baseline: Simulation, run_event: RunEvent
) -> None:
    sim = run_event("channel_opportunity", START, 10, {"campaign": "g_pmax_catalogue"})
    pmax = slots_where(baseline, campaign="g_pmax_catalogue")
    siblings = slots_where(baseline, channel="google_ads") & ~pmax
    a, b = day(3), day(9)

    def orders(s: Simulation, slots: np.ndarray) -> float:
        return total(s.paid.funnel.purchases, s, a, b, slots)

    assert orders(sim, pmax) > 1.15 * orders(baseline, pmax)
    assert abs(orders(sim, siblings) / orders(baseline, siblings) - 1) < 0.05


def test_tracking_break_drops_platform_conversions_but_not_orders(
    baseline: Simulation, run_event: RunEvent
) -> None:
    sim = run_event("tracking_break", START, 4, {"source": "meta_ads"})
    meta = ~slots_where(baseline, channel="google_ads")
    a, b = START, day(3)
    conv0, conv1 = baseline.paid.platform_conversions, sim.paid.platform_conversions
    assert total(conv1, sim, a, b, meta) < 0.3 * total(conv0, baseline, a, b, meta)
    np.testing.assert_array_equal(sim.store.orders, baseline.store.orders)
    np.testing.assert_array_equal(conv1[:, ~meta], conv0[:, ~meta])


def test_budget_overpace_spends_ahead_of_plan_on_one_channel(
    baseline: Simulation, run_event: RunEvent
) -> None:
    sim = run_event("budget_overpace", day(-1), 12, {"channel": "meta_ads"})
    meta = slots_where(baseline, channel="meta_ads")
    a, b = day(-1), day(10)
    spend0, spend1 = baseline.delivery.spend, sim.delivery.spend
    assert 1.3 < total(spend1, sim, a, b, meta) / total(spend0, baseline, a, b, meta) < 1.46
    np.testing.assert_array_equal(spend1[:, ~meta], spend0[:, ~meta])


def test_no_issue_changes_nothing(baseline: Simulation, run_event: RunEvent) -> None:
    sim = run_event("no_issue", START, 7, {})
    np.testing.assert_array_equal(sim.delivery.clicks, baseline.delivery.clicks)
    np.testing.assert_array_equal(sim.store.orders, baseline.store.orders)
    assert [e.type for e in sim.events] == ["no_issue"]
