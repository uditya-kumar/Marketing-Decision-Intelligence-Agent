from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

import numpy as np
import pytest

from novawear_sim.world.festive import calendar_effects
from novawear_sim.world.timeline import Timeline

if TYPE_CHECKING:
    from novawear_sim.config.models import WorldConfig
    from novawear_sim.engine import Simulation


def test_calendar_multipliers_are_neutral_outside_events(config: WorldConfig) -> None:
    timeline = Timeline.between(date(2026, 4, 1), date(2026, 4, 30))
    effects = calendar_effects(config.calendar, timeline)
    for series in (effects.demand, effects.cpm, effects.aov):
        np.testing.assert_allclose(series, 1.0)


@pytest.mark.parametrize(("name", "uplift"), [("Diwali 2025", 1.5), ("Winter EOSS 2025", 1.25)])
def test_orders_spike_on_configured_dates(
    baseline: Simulation, config: WorldConfig, name: str, uplift: float
) -> None:
    event = next(e for e in config.calendar if e.name == name)
    peak = event.peak or event.start
    orders = baseline.store.orders
    around = baseline.timeline.mask(peak - timedelta(days=1), peak + timedelta(days=1))
    before = baseline.timeline.mask(
        event.start - timedelta(days=21), event.start - timedelta(days=8)
    )
    assert orders[around].mean() > uplift * orders[before].mean()


def test_diwali_raises_cpm(baseline: Simulation, config: WorldConfig) -> None:
    diwali = next(e for e in config.calendar if e.name == "Diwali 2025")
    effects = baseline.festive
    peak = baseline.timeline.mask(diwali.peak or diwali.start, diwali.peak or diwali.start)
    assert effects.cpm[peak][0] > 1.1
    assert effects.demand[peak][0] > 1.3
