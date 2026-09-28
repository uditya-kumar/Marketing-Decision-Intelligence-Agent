"""Platform, web and store numbers disagree like real ones do, and reconcile within tolerance."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import numpy as np
import pytest

from helpers import slots_where, total

if TYPE_CHECKING:
    from novawear_sim.config.models import WorldConfig
    from novawear_sim.engine import Simulation

START, END = date(2025, 10, 1), date(2026, 3, 31)


def test_store_orders_are_all_true_purchases(baseline: Simulation) -> None:
    expected = baseline.paid.funnel.purchases.sum(axis=1) + baseline.organic.purchases.sum(axis=1)
    np.testing.assert_array_equal(baseline.store.orders, expected)


def test_web_analytics_undercounts_store_orders(baseline: Simulation, config: WorldConfig) -> None:
    days = baseline.timeline.mask(START, END)
    ratio = baseline.web.recorded.purchases[days].sum() / baseline.store.orders[days].sum()
    assert abs(ratio - config.funnel.ga_capture) < 0.03
    assert ratio < 1


@pytest.mark.parametrize("channel", ["google_ads", "meta_ads", "instagram"])
def test_platforms_over_claim_by_their_attribution_ratio(
    baseline: Simulation, config: WorldConfig, channel: str
) -> None:
    slots = slots_where(baseline, channel=channel)
    claimed = total(baseline.paid.platform_conversions, baseline, START, END, slots)
    true = total(baseline.paid.funnel.purchases, baseline, START, END, slots)
    ratio = next(c.attribution_ratio for c in config.channels if c.key == channel)
    assert claimed > true
    assert abs(claimed / true - ratio) < 0.08 * ratio


def test_platform_conversions_exceed_store_orders_from_paid(baseline: Simulation) -> None:
    days = baseline.timeline.mask(START, END)
    claimed = baseline.paid.platform_conversions[days].sum()
    store_paid = baseline.paid.funnel.purchases[days].sum()
    assert 1.1 < claimed / store_paid < 1.4


def test_store_money_columns_add_up(baseline: Simulation, config: WorldConfig) -> None:
    s = baseline.store
    np.testing.assert_allclose(s.net_sales, s.gross_sales - s.discounts - s.returns, atol=0.02)
    np.testing.assert_allclose(s.total_sales, s.net_sales + s.shipping + s.taxes, atol=0.02)
    np.testing.assert_array_equal(s.new_customers + s.returning_customers, s.orders)
    assert np.all(s.discounts >= 0) and np.all(s.returns >= 0)
