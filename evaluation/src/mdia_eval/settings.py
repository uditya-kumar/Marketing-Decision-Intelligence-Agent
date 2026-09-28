"""The business settings a NovaWear marketer would have entered (FR-1), read from the
generator's world file so the two never drift.

The generator's ``world.yaml`` is the hidden truth, but budgets, margin and sale windows
are things the *user* knows and types into settings, so using them here is fair game.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import yaml
from mdia.domain.periods import Period

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from mdia.domain.sources import Channel

_DEFAULT = "default"
# A long sale is an expected change a marketer would mark; a three-day holiday is not.
MIN_FESTIVE_DAYS = 7


@dataclass(frozen=True, slots=True)
class EvalSettings:
    gross_margin_pct: float
    # Export source → one month-to-budget plan per simulation channel (Instagram is Meta's).
    budgets: Mapping[Channel, Sequence[Mapping[str, float]]]
    festive: Sequence[Period] = ()

    def month_budgets(self, as_of: dt.date) -> dict[Channel, float]:
        month = f"{as_of:%Y-%m}"
        return {
            channel: sum(plan.get(month, plan[_DEFAULT]) for plan in plans)
            for channel, plans in self.budgets.items()
        }


def load(path: Path) -> EvalSettings:
    world: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    budgets: dict[Channel, list[Mapping[str, float]]] = {}
    for channel in world["channels"]:
        plan = {str(month): float(amount) for month, amount in channel["monthly_budget"].items()}
        budgets.setdefault(channel["source"], []).append(plan)
    return EvalSettings(
        gross_margin_pct=float(world["brand"]["gross_margin"]) * 100,
        budgets=budgets,
        festive=_festive(world["calendar"]),
    )


def _festive(calendar: Sequence[Mapping[str, Any]]) -> tuple[Period, ...]:
    windows = [(_date(w["start"]), _date(w["end"])) for w in calendar]
    return tuple(
        Period(start, end) for start, end in windows if (end - start).days >= MIN_FESTIVE_DAYS
    )


def _date(value: Any) -> dt.date:
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value))
