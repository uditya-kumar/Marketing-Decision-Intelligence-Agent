"""Budget pacing per channel (FR-7), computed on request and never stored."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mdia.domain.pacing import pace
from mdia.domain.periods import month_to_date
from mdia.domain.sources import CHANNELS
from mdia.repositories.metrics import MetricsRepository

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Mapping

    from sqlalchemy.orm import Session

    from mdia.domain.pacing import Pacing
    from mdia.domain.periods import Period
    from mdia.domain.sources import Channel


@dataclass(frozen=True, slots=True)
class ChannelPacing:
    channel: Channel
    pacing: Pacing


@dataclass(frozen=True, slots=True)
class PacingView:
    month: Period | None
    # All budgeted channels together; ``None`` when no budget is set.
    total: Pacing | None
    channels: list[ChannelPacing]


class PacingService:
    def __init__(self, session: Session) -> None:
        self._metrics = MetricsRepository(session)

    def month(self, as_of: dt.date | None, budgets: Mapping[str, float]) -> PacingView:
        """Month-to-date spend of each channel with a budget, through ``as_of``."""
        budgeted = {c: float(budgets[c]) for c in CHANNELS if budgets.get(c)}
        if as_of is None or not budgeted:
            return PacingView(None, None, [])
        month = month_to_date(as_of)
        spent: dict[str, float] = {}
        for row in self._metrics.ad_daily(month, "channel"):
            spent[row["key"]] = spent.get(row["key"], 0.0) + float(row["spend"])
        channels = [
            ChannelPacing(c, pace(budget, spent.get(c, 0.0), as_of))
            for c, budget in budgeted.items()
        ]
        total = pace(sum(budgeted.values()), sum(spent.get(c, 0.0) for c in budgeted), as_of)
        return PacingView(month, total, channels)
