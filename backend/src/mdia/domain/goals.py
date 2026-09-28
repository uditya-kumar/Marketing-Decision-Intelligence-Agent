"""Goals (FR-1.2): break-even ROAS and whether a metric is ahead of, on or behind target."""

from __future__ import annotations

from typing import Literal

GoalStatus = Literal["ahead", "on_track", "behind"]

# Within ±5 % of target counts as on track, so day-to-day noise doesn't flip the status.
ON_TRACK_TOLERANCE = 0.05


def break_even_roas(gross_margin_pct: float) -> float:
    """ROAS at which ad spend exactly eats the gross margin: ``1 / margin``."""
    if not 0 < gross_margin_pct <= 100:
        raise ValueError("gross margin must be in (0, 100] %")
    return 100 / gross_margin_pct


def is_profitable_roas(roas: float, gross_margin_pct: float) -> bool:
    """Whether ``roas`` more than covers the product cost, i.e. beats break-even."""
    return roas > break_even_roas(gross_margin_pct)


def goal_status(
    actual: float,
    target: float,
    *,
    higher_is_better: bool = True,
    tolerance: float = ON_TRACK_TOLERANCE,
) -> GoalStatus:
    """Compare ``actual`` with ``target``; for cost metrics (CPA) lower is better."""
    if target <= 0:
        raise ValueError("target must be positive")
    if higher_is_better:
        ratio = actual / target
    elif actual <= 0:
        # A zero cost per sale can only mean no spend: nothing to be behind on.
        return "ahead"
    else:
        ratio = target / actual
    if ratio >= 1 + tolerance:
        return "ahead"
    if ratio >= 1 - tolerance:
        return "on_track"
    return "behind"


def prorated_target(monthly_target: float, days_elapsed: int, days_in_month: int) -> float:
    """The share of a monthly target that should be reached after ``days_elapsed`` days."""
    if not 0 <= days_elapsed <= days_in_month:
        raise ValueError("days_elapsed must be within the month")
    return monthly_target * days_elapsed / days_in_month
