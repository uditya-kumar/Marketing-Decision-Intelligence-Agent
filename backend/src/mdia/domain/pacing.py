"""Budget pacing (FR-7): is month-to-date spend on course to land on the monthly budget?"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from mdia.domain.periods import days_in_month

if TYPE_CHECKING:
    import datetime as dt

PacingStatus = Literal["on_track", "over", "under"]

# Daily spend is lumpy, so a projection within ±10 % of budget still counts as on plan.
PACE_TOLERANCE = 0.10


@dataclass(frozen=True, slots=True)
class Pacing:
    budget: float
    spent: float
    spent_pct: float
    # Budget minus spend; negative once the month's budget is overspent.
    remaining_budget: float
    month_elapsed_pct: float
    projected: float
    status: PacingStatus
    # Average daily spend so far this month.
    daily_run_rate: float
    # Daily spend over the remaining days that lands exactly on budget; ``None`` on the
    # month's last day, when nothing is left to adjust.
    suggested_daily: float | None


def pace(budget: float, spent: float, day: dt.date) -> Pacing:
    """Pacing after ``day``'s spend, projecting the month-to-date run rate to month end."""
    if budget <= 0:
        raise ValueError("budget must be positive")
    if spent < 0:
        raise ValueError("spend can't be negative")
    elapsed, total = day.day, days_in_month(day)
    run_rate = spent / elapsed
    projected = run_rate * total
    days_left = total - elapsed
    return Pacing(
        budget=budget,
        spent=spent,
        spent_pct=spent / budget * 100,
        remaining_budget=budget - spent,
        month_elapsed_pct=elapsed / total * 100,
        projected=projected,
        status=pacing_status(projected, budget),
        daily_run_rate=run_rate,
        suggested_daily=max(budget - spent, 0) / days_left if days_left else None,
    )


def pacing_status(
    projected: float, budget: float, tolerance: float = PACE_TOLERANCE
) -> PacingStatus:
    ratio = projected / budget
    if ratio > 1 + tolerance:
        return "over"
    if ratio < 1 - tolerance:
        return "under"
    return "on_track"
