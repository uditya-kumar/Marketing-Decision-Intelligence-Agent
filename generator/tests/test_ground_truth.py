from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING, Any

import pytest

from conftest import END, SEED, RunEvent
from novawear_sim.config.schedule import Schedule, ScheduledEvent, Target
from novawear_sim.engine import simulate
from novawear_sim.errors import ScenarioError
from novawear_sim.scenarios.ground_truth import GroundTruth

if TYPE_CHECKING:
    from pathlib import Path

    from novawear_sim.config.models import WorldConfig

START = date(2026, 2, 2)


def _event(id_: str, type_: str, start: date, days: int, **target: Any) -> ScheduledEvent:
    return ScheduledEvent(id=id_, type=type_, start=start, days=days, target=Target(**target))


def test_no_op_scenario_writes_a_ground_truth_entry(run_event: RunEvent, tmp_path: Path) -> None:
    sim = run_event("no_issue", START, 7, {})
    path = tmp_path / "ground_truth.json"
    GroundTruth.for_window(
        sim.events, version="test", seed=SEED, schedule="t", start=START, end=END
    ).write(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["seed"] == SEED
    [entry] = data["events"]
    assert entry["type"] == "no_issue"
    assert entry["start"] == "2026-02-02" and entry["end"] == "2026-02-08"
    assert entry["target"]["level"] == "account"
    assert entry["expected_signal_type"] is None


def test_entry_describes_the_target_with_names_and_platform_ids(run_event: RunEvent) -> None:
    [entry] = run_event("creative_fatigue", START, 10, {"creative": "fb_lookalike_c1"}).events
    t = entry.target
    assert (t.level, t.source, t.channel) == ("creative", "meta_ads", "meta_ads")
    assert t.creative == "Video | Customer Stories"
    assert t.platform_id is not None and t.platform_id.startswith("120")
    assert entry.expected_signal_type == "creative"
    assert entry.expected_action == "rotate_creative"
    assert {m.metric for m in entry.affected_metrics} >= {"ctr", "frequency"}


def test_window_keeps_only_overlapping_events(run_event: RunEvent) -> None:
    events = run_event("no_issue", START, 7, {}).events
    kw: dict[str, Any] = {"version": "t", "seed": 1, "schedule": "t"}
    assert GroundTruth.for_window(events, start=date(2026, 2, 8), end=date(2026, 2, 9), **kw).events
    assert not GroundTruth.for_window(
        events, start=date(2026, 2, 9), end=date(2026, 3, 1), **kw
    ).events


@pytest.mark.parametrize(
    ("events", "message"),
    [
        ([_event("a", "nope", START, 3)], "unknown scenario"),
        ([_event("a", "cpc_spike", START, 3, creative="fb_cart_c1")], "targets"),
        ([_event("a", "creative_fatigue", START, 3, creative="g_brand_rsa_1")], "do not fatigue"),
        ([_event("a", "no_issue", START, 3), _event("a", "no_issue", START, 3)], "unique"),
        (
            [
                _event("q", "no_issue", START, 7),
                _event("x", "cpc_spike", START, 3, channel="meta_ads"),
            ],
            "quiet window",
        ),
        ([_event("a", "cpc_spike", START, 3, channel="tiktok")], "tiktok"),
    ],
)
def test_invalid_schedules_are_rejected(
    config: WorldConfig, events: list[ScheduledEvent], message: str
) -> None:
    with pytest.raises(ScenarioError, match=message):
        simulate(config, Schedule(events=events), SEED, END)


def test_invalid_params_are_rejected(run_event: RunEvent) -> None:
    with pytest.raises(ScenarioError, match="invalid params"):
        run_event("cpc_spike", START, 3, {"channel": "meta_ads"}, cpm_multiplier=0.5, typo=1)
