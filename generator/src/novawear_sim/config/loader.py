"""Load and validate the YAML configs (packaged defaults or user-supplied paths)."""

from __future__ import annotations

from importlib import resources
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import ValidationError

from novawear_sim.config.models import WorldConfig
from novawear_sim.config.schedule import Schedule, ScheduleFile
from novawear_sim.errors import ConfigError

if TYPE_CHECKING:
    from pathlib import Path

EMPTY_SCHEDULE = "none"


def _read_yaml(path: Path | None, default_name: str) -> tuple[Any, str]:
    if path is None:
        resource = resources.files("novawear_sim.config").joinpath(default_name)
        return yaml.safe_load(resource.read_text(encoding="utf-8")), default_name
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")), str(path)


def load_world(path: Path | None = None) -> WorldConfig:
    raw, origin = _read_yaml(path, "world.yaml")
    try:
        return WorldConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"invalid world config {origin}:\n{exc}") from exc


def load_schedules(path: Path | None = None) -> dict[str, Schedule]:
    raw, origin = _read_yaml(path, "scenarios.yaml")
    try:
        schedules = ScheduleFile.model_validate(raw).schedules
    except ValidationError as exc:
        raise ConfigError(f"invalid scenario config {origin}:\n{exc}") from exc
    return {EMPTY_SCHEDULE: Schedule(description="No injected scenarios."), **schedules}


def load_schedule(name: str, path: Path | None = None) -> Schedule:
    schedules = load_schedules(path)
    if name not in schedules:
        raise ConfigError(f"unknown schedule {name!r}; available: {sorted(schedules)}")
    return schedules[name]
