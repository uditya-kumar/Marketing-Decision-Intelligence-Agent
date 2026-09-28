from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import numpy as np
from hypothesis import given
from hypothesis import strategies as st

from helpers import slots_where, total
from novawear_sim.config.channels import Hill
from novawear_sim.world.saturation import efficiency, hill_response, yield_preserving_vmax

if TYPE_CHECKING:
    from conftest import RunEvent
    from novawear_sim.engine import Simulation

HILL = Hill(vmax=1.0, k=20000, slope=1.1, reference_spend=15000)
# A slope > 1 makes the curve S-shaped below ~k/15; channels always spend far past that.
spends = st.floats(min_value=HILL.k / 4, max_value=1_000_000)


def test_efficiency_is_one_at_reference_spend() -> None:
    assert np.isclose(efficiency(HILL.reference_spend, HILL), 1.0)


@given(spends)
def test_doubling_spend_less_than_doubles_response(spend: float) -> None:
    assert hill_response(2 * spend, HILL) < 2 * hill_response(spend, HILL)


@given(spends, st.floats(min_value=1.01, max_value=3))
def test_response_increases_with_spend(spend: float, factor: float) -> None:
    assert hill_response(spend * factor, HILL) > hill_response(spend, HILL)


@given(st.floats(min_value=1.0, max_value=3.0))
def test_yield_preserving_vmax_keeps_reference_efficiency(headroom: float) -> None:
    vmax = yield_preserving_vmax(HILL, headroom)
    assert np.isclose(efficiency(HILL.reference_spend, HILL, vmax, headroom), 1.0)
    # …while doubling spend now pays back better than before.
    assert efficiency(2 * HILL.reference_spend, HILL, vmax, headroom) >= efficiency(
        2 * HILL.reference_spend, HILL
    )


def test_doubling_a_channel_budget_less_than_doubles_its_conversions(
    baseline: Simulation, run_event: RunEvent
) -> None:
    start, end = date(2026, 2, 1), date(2026, 2, 28)
    doubled = run_event("budget_overpace", start, 28, {"channel": "meta_ads"}, factor=2.0)
    slots = slots_where(baseline, channel="meta_ads")

    def spend_and_orders(sim: Simulation) -> tuple[float, float]:
        return (
            total(sim.delivery.spend, sim, start, end, slots),
            total(sim.paid.funnel.purchases, sim, start, end, slots),
        )

    base_spend, base_orders = spend_and_orders(baseline)
    new_spend, new_orders = spend_and_orders(doubled)
    assert 1.9 < new_spend / base_spend < 2.1
    assert base_orders < new_orders < 2 * base_orders
    assert new_orders / new_spend < base_orders / base_spend
