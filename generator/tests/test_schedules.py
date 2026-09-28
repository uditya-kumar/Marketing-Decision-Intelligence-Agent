"""The packaged demo and evaluation schedules generate and respect their design constraints."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import TYPE_CHECKING

import pytest

from conftest import SEED
from novawear_sim.config.loader import load_schedule
from novawear_sim.engine import Simulation, simulate

if TYPE_CHECKING:
    from novawear_sim.config.models import WorldConfig
    from novawear_sim.scenarios.ground_truth import GroundTruthEvent

EVAL_START, EVAL_END = date(2025, 10, 15), date(2026, 10, 14)
QUIET = "no_issue"


@pytest.fixture(scope="module")
def evaluation(config: WorldConfig) -> Simulation:
    return simulate(config, load_schedule("evaluation"), SEED, EVAL_END)


def _channels(event: GroundTruthEvent) -> set[str]:
    t = event.target
    if t.level == "account":
        return {"google_ads", "meta_ads", "instagram"}
    if t.level == "source":
        return {"google_ads"} if t.source == "google_ads" else {"meta_ads", "instagram"}
    assert t.channel is not None
    return {t.channel}


def test_demo_schedule_generates(config: WorldConfig) -> None:
    sim = simulate(config, load_schedule("demo"), SEED, date(2026, 10, 28))
    assert len(sim.events) == 8
    assert {e.type for e in sim.events} >= {"creative_fatigue", "budget_overpace", "tracking_break"}


def test_evaluation_schedule_has_about_fifty_labelled_events(evaluation: Simulation) -> None:
    counts = Counter(e.type for e in evaluation.events)
    assert 45 <= len(evaluation.events) <= 55
    assert counts[QUIET] >= 6
    assert len(counts) == 8  # every scenario type appears
    assert all(e.start >= EVAL_START and e.end <= EVAL_END for e in evaluation.events)


def test_evaluation_events_on_a_channel_never_overlap(evaluation: Simulation) -> None:
    gap = timedelta(days=3)
    events = evaluation.events
    for i, a in enumerate(events):
        for b in events[i + 1 :]:
            if _channels(a) & _channels(b):
                assert not (a.start - gap <= b.end and b.start <= a.end + gap), (a.id, b.id)


def test_injected_evaluation_events_avoid_festive_windows(
    evaluation: Simulation, config: WorldConfig
) -> None:
    for e in (e for e in evaluation.events if e.type != QUIET):
        for f in config.calendar:
            assert not (e.start <= f.end and f.start <= e.end), (e.id, f.name)


def test_some_quiet_windows_sit_inside_festive_periods(
    evaluation: Simulation, config: WorldConfig
) -> None:
    festive_quiet = [
        e
        for e in evaluation.events
        if e.type == QUIET and any(e.start <= f.end and f.start <= e.end for f in config.calendar)
    ]
    assert len(festive_quiet) >= 2
