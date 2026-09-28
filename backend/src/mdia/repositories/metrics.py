"""Daily sums of base measures for KPI queries. Ratios are never computed here."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import case, func, select

from mdia.models import (
    DimAdSet,
    DimCampaign,
    DimChannel,
    DimCreative,
    FactAdDaily,
    FactStoreDaily,
)
from mdia.repositories.facts import AD_MEASURES

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement, Select
    from sqlalchemy.orm import Session

    from mdia.domain.kpi import Dimension
    from mdia.domain.periods import Period

type Row = dict[str, Any]

# Slice → (key column, display-name column, dimension table to join for the name).
_SLICES: dict[Dimension, tuple[Any, Any, Any]] = {
    "channel": (FactAdDaily.channel_id, DimChannel.name, DimChannel),
    "campaign": (FactAdDaily.campaign_id, DimCampaign.name, DimCampaign),
    "ad_set": (FactAdDaily.ad_set_id, DimAdSet.name, DimAdSet),
    "creative": (FactAdDaily.creative_id, DimCreative.name, DimCreative),
    "age_group": (FactAdDaily.age_group, FactAdDaily.age_group, None),
}


class MetricsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def ad_daily(self, period: Period, dimension: Dimension | None = None) -> list[Row]:
        """Ad measures summed per day, and per ``dimension`` value when one is given.

        Rows carry ``date`` and the measures; sliced rows also carry ``key`` and ``name``.
        """
        sums = [_sum(m) for m in AD_MEASURES]
        in_period = FactAdDaily.date.between(period.start, period.end)
        if dimension is None:
            stmt: Select[Any] = select(FactAdDaily.date, *sums).group_by(FactAdDaily.date)
        else:
            key, name, table = _SLICES[dimension]
            stmt = select(FactAdDaily.date, key.label("key"), name.label("name"), *sums)
            if table is not None:
                stmt = stmt.join(table, table.id == key)
            stmt = stmt.group_by(FactAdDaily.date, key, name)
        return [dict(row) for row in self._session.execute(stmt.where(in_period)).mappings()]

    def store_daily(self, period: Period) -> list[Row]:
        """Store orders and net revenue per day, as ``store_orders`` / ``store_revenue``."""
        stmt = select(
            FactStoreDaily.date,
            FactStoreDaily.orders.label("store_orders"),
            FactStoreDaily.revenue.label("store_revenue"),
        ).where(FactStoreDaily.date.between(period.start, period.end))
        return [dict(row) for row in self._session.execute(stmt).mappings()]


def _sum(measure: str) -> ColumnElement[Any]:
    column = getattr(FactAdDaily, measure)
    if measure != "reach":
        return func.sum(column).label(measure)
    # Google reports no reach; a sum over only the Meta rows would inflate frequency.
    complete = func.count(column) == func.count()
    return case((complete, func.sum(column))).label(measure)
