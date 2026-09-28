from __future__ import annotations

from pathlib import Path

import pytest

from novawear_sim.config.loader import EMPTY_SCHEDULE, load_schedule, load_schedules, load_world
from novawear_sim.config.models import WorldConfig
from novawear_sim.errors import ConfigError


def test_packaged_world_loads_into_typed_models(config: WorldConfig) -> None:
    assert isinstance(config, WorldConfig)
    assert [c.key for c in config.channels] == ["google_ads", "meta_ads", "instagram"]
    assert config.timeline.epoch < config.timeline.default_end
    for channel in config.channels:
        assert channel.monthly_budget.default > 0
        assert all(len(camp.ad_sets) >= 1 for camp in channel.campaigns)


def test_monthly_budget_override(config: WorldConfig) -> None:
    google = config.channels[0].monthly_budget
    assert google.for_month(2025, 10) != google.default
    assert google.for_month(2026, 1) == google.default


def test_packaged_schedules_load() -> None:
    schedules = load_schedules()
    assert {"demo", "evaluation", EMPTY_SCHEDULE} <= set(schedules)
    assert load_schedule(EMPTY_SCHEDULE).events == []


def test_unknown_schedule_is_a_config_error() -> None:
    with pytest.raises(ConfigError, match="unknown schedule"):
        load_schedule("does-not-exist")


def test_missing_file_is_a_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_world(tmp_path / "missing.yaml")


def test_invalid_world_is_a_config_error(tmp_path: Path) -> None:
    path = tmp_path / "world.yaml"
    path.write_text("brand: {name: X}\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="invalid world config"):
        load_world(path)


def test_duplicate_keys_are_rejected(tmp_path: Path) -> None:
    text = (Path(__file__).parents[1] / "src/novawear_sim/config/world.yaml").read_text("utf-8")
    path = tmp_path / "world.yaml"
    path.write_text(text.replace("key: g_sarees\n", "key: g_kurtas\n"), encoding="utf-8")
    with pytest.raises(ConfigError, match="g_kurtas"):
        load_world(path)
