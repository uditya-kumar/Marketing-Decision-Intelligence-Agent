from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from novawear_sim.config.loader import load_schedule
from novawear_sim.config.schedule import Schedule
from novawear_sim.engine import Simulation, simulate
from novawear_sim.exporters.writer import EXPORTS, write_window
from novawear_sim.world.demand import demand_index, weekly_profile
from novawear_sim.world.festive import calendar_effects
from novawear_sim.world.rng import RandomStreams
from novawear_sim.world.timeline import Timeline

if TYPE_CHECKING:
    from pathlib import Path

    from novawear_sim.config.models import WorldConfig

END = date(2025, 12, 31)


def _arrays(sim: Simulation) -> list[np.ndarray]:
    return [
        sim.demand,
        sim.delivery.spend,
        sim.delivery.clicks,
        sim.paid.platform_conversions,
        sim.web.recorded.sessions,
        sim.store.total_sales,
    ]


def test_demand_is_reproducible_for_a_seed(config: WorldConfig) -> None:
    timeline = Timeline.between(config.timeline.epoch, END)
    festive = calendar_effects(config.calendar, timeline).demand

    def run(seed: int) -> np.ndarray:
        streams = RandomStreams(seed, timeline.ordinals)
        return demand_index(config.demand, timeline, festive, streams)

    np.testing.assert_array_equal(run(42), run(42))
    assert not np.allclose(run(42), run(43))


def test_weekly_profile_has_mean_one_and_weekend_peak(config: WorldConfig) -> None:
    profile = weekly_profile(config.demand)
    assert np.isclose(profile.mean(), 1.0)
    assert profile[5:].mean() > profile[:5].mean()


def test_same_seed_gives_identical_simulation(config: WorldConfig) -> None:
    a = simulate(config, Schedule(), 42, END)
    b = simulate(config, Schedule(), 42, END)
    for x, y in zip(_arrays(a), _arrays(b), strict=True):
        np.testing.assert_array_equal(x, y)


def test_different_seed_gives_different_simulation(config: WorldConfig) -> None:
    a = simulate(config, Schedule(), 42, END)
    b = simulate(config, Schedule(), 7, END)
    assert not np.array_equal(a.delivery.clicks, b.delivery.clicks)


def test_batch_equals_the_matching_slice_of_a_longer_backfill(
    config: WorldConfig, tmp_path: Path
) -> None:
    schedule = load_schedule("demo")
    batch_start, batch_end = date(2026, 10, 15), date(2026, 10, 21)
    short = simulate(config, schedule, 42, batch_end)
    long = simulate(config, schedule, 42, date(2026, 11, 30))
    write_window(short, "demo", batch_start, batch_end, tmp_path / "batch")
    write_window(long, "demo", batch_start, batch_end, tmp_path / "slice")
    for name in EXPORTS:
        pd.testing.assert_frame_equal(
            pd.read_csv(tmp_path / "batch" / name), pd.read_csv(tmp_path / "slice" / name)
        )
