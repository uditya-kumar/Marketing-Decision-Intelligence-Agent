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
    FactWebDaily,
)
from mdia.repositories.facts import AD_MEASURES

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement, Select
    from sqlalchemy.orm import Session

    from mdia.domain.kpi import Dimension
    from mdia.domain.periods import Period

type Row = dict[str, Any]

WEB_MEASURES = ("sessions", "bounces", "add_to_cart", "checkout", "purchases")

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

    def entity_daily(self, period: Period) -> list[Row]:
        """Ad measures per day at the finest level the detectors work on (FR-6).

        One wide result the whole sweep rolls up in pandas, rather than a query per
        level: day × channel × campaign × ad set × creative × age group, with names.
        """
        keys = (
            FactAdDaily.date,
            FactAdDaily.channel_id,
            FactAdDaily.campaign_id,
            DimCampaign.name.label("campaign_name"),
            FactAdDaily.ad_set_id,
            DimAdSet.name.label("ad_set_name"),
            FactAdDaily.creative_id,
            DimCreative.name.label("creative_name"),
            FactAdDaily.age_group,
        )
        stmt = (
            select(*keys, *(_sum(m) for m in AD_MEASURES))
            .join(DimCampaign, DimCampaign.id == FactAdDaily.campaign_id)
            .join(DimAdSet, DimAdSet.id == FactAdDaily.ad_set_id)
            .join(DimCreative, DimCreative.id == FactAdDaily.creative_id)
            .where(FactAdDaily.date.between(period.start, period.end))
            .group_by(*keys)
        )
        return [dict(row) for row in self._session.execute(stmt).mappings()]

    def web_daily(self, period: Period) -> list[Row]:
        """Funnel steps per day and session source / medium."""
        sums = [func.sum(getattr(FactWebDaily, m)).label(m) for m in WEB_MEASURES]
        stmt = (
            select(FactWebDaily.date, FactWebDaily.source, *sums)
            .where(FactWebDaily.date.between(period.start, period.end))
            .group_by(FactWebDaily.date, FactWebDaily.source)
        )
        return [dict(row) for row in self._session.execute(stmt).mappings()]

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
