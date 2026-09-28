"""Shared fixtures: the packaged world, a cached baseline run, and single-event runs."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import TYPE_CHECKING, Any

import pytest

from novawear_sim.config.loader import load_world
from novawear_sim.config.schedule import Schedule, ScheduledEvent, Target
from novawear_sim.engine import Simulation, simulate

if TYPE_CHECKING:
    from novawear_sim.config.models import WorldConfig

SEED = 42
# Long enough for festive season + a quiet Q1 to inject scenarios into, short enough to be fast.
END = date(2026, 3, 31)

RunEvent = Callable[..., Simulation]


@pytest.fixture(scope="session")
def config() -> WorldConfig:
    return load_world()


@pytest.fixture(scope="session")
def baseline(config: WorldConfig) -> Simulation:
    return simulate(config, Schedule(), SEED, END)


@pytest.fixture(scope="session")
def run_event(config: WorldConfig) -> RunEvent:
    """Simulate the world with one scheduled event (same seed as `baseline`)."""

    def run(
        type_: str, start: date, days: int, target: dict[str, Any], **params: Any
    ) -> Simulation:
        event = ScheduledEvent(
            id="test_event",
            type=type_,
            start=start,
            days=days,
            target=Target(**target),
            params=params,
        )
        return simulate(config, Schedule(events=[event]), SEED, END)

    return run
