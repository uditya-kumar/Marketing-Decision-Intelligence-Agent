"""Baseline KPIs land in ranges typical of an Indian D2C fashion brand."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import numpy as np
import pytest

from helpers import slots_where, total

if TYPE_CHECKING:
    from novawear_sim.engine import Simulation

START, END = date(2026, 1, 11), date(2026, 3, 31)

# channel: (CTR, CPC ₹, CPM ₹, platform CPA ₹, platform ROAS)
RANGES = {
    "google_ads": ((0.015, 0.06), (6, 30), (100, 600), (200, 900), (2.0, 8.0)),
    "meta_ads": ((0.007, 0.025), (5, 25), (60, 250), (200, 900), (2.0, 8.0)),
    "instagram": ((0.005, 0.02), (5, 25), (50, 250), (400, 1600), (1.0, 4.0)),
}


@pytest.mark.parametrize("channel", list(RANGES))
def test_channel_kpis_are_realistic(baseline: Simulation, channel: str) -> None:
    ctr_r, cpc_r, cpm_r, cpa_r, roas_r = RANGES[channel]
    slots = slots_where(baseline, channel=channel)
    d, p = baseline.delivery, baseline.paid
    spend = total(d.spend, baseline, START, END, slots)
    impressions = total(d.impressions, baseline, START, END, slots)
    clicks = total(d.clicks, baseline, START, END, slots)
    conversions = total(p.platform_conversions, baseline, START, END, slots)
    revenue = total(p.platform_revenue, baseline, START, END, slots)

    assert ctr_r[0] < clicks / impressions < ctr_r[1]
    assert cpc_r[0] < spend / clicks < cpc_r[1]
    assert cpm_r[0] < spend / impressions * 1000 < cpm_r[1]
    assert cpa_r[0] < spend / conversions < cpa_r[1]
    assert roas_r[0] < revenue / spend < roas_r[1]


def test_meta_daily_frequency_is_realistic(baseline: Simulation) -> None:
    slots = ~slots_where(baseline, channel="google_ads")
    d = baseline.delivery
    freq = total(d.impressions, baseline, START, END, slots) / total(
        d.reach, baseline, START, END, slots
    )
    assert 1.0 < freq < 2.0


def test_store_kpis_are_realistic(baseline: Simulation) -> None:
    days = baseline.timeline.mask(START, END)
    s = baseline.store
    orders = s.orders[days].sum()
    spend = baseline.delivery.spend[days].sum()
    assert 60 < orders / days.sum() < 250
    assert 1200 < s.net_sales[days].sum() / orders < 3000  # AOV
    assert 2.0 < s.net_sales[days].sum() / spend < 8.0  # MER
    assert 0.3 < s.new_customers[days].sum() / orders < 0.8


def test_web_bounce_rate_is_realistic(baseline: Simulation) -> None:
    days = baseline.timeline.mask(START, END)
    rec = baseline.web.recorded
    bounce = 1 - rec.engaged[days].sum() / rec.sessions[days].sum()
    assert 0.3 < bounce < 0.55


def test_funnel_is_monotone_everywhere(baseline: Simulation) -> None:
    for counts in (baseline.paid.funnel, baseline.organic, baseline.web.recorded):
        steps = [counts.sessions, counts.engaged, counts.add_to_cart, counts.checkout]
        for upper, lower in zip(steps, [*steps[1:], counts.purchases], strict=True):
            assert np.all(lower <= upper)
