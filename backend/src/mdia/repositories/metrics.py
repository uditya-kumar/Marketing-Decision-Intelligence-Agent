"""Daily sums of base measures for KPI queries. Ratios are never computed here."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from sqlalchemy import ColumnElement, case, func, select

from mdia.domain.sources import PAID_WEB_SOURCES
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
    from collections.abc import Sequence

    from sqlalchemy import Select
    from sqlalchemy.orm import Session

    from mdia.domain.kpi import Dimension
    from mdia.domain.periods import Period

type Row = dict[str, Any]

WEB_MEASURES = ("sessions", "bounces", "add_to_cart", "checkout", "purchases")
STORE_SUMS = ("store_orders", "store_revenue")

# Entity levels that are a column of the ad facts, and the column that holds them.
_ENTITY_KEYS: dict[str, Any] = {
    "channel": FactAdDaily.channel_id,
    "campaign": FactAdDaily.campaign_id,
    "ad_set": FactAdDaily.ad_set_id,
    "creative": FactAdDaily.creative_id,
}
# Entity keys that are database ids rather than names, so the filter has to bind an int.
_NUMERIC_LEVELS = frozenset({"campaign", "ad_set", "creative"})


@dataclass(frozen=True, slots=True)
class Totals:
    """Base measures summed over a window, and the days of it that had any rows."""

    measures: dict[str, float] = field(default_factory=dict)
    days: int = 0

    def merge(self, other: Totals) -> Totals:
        """Measures from another table, and the fullest coverage either of them had."""
        return Totals(self.measures | other.measures, max(self.days, other.days))


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

    def entity_totals(self, period: Period, level: str, key: str) -> Totals:
        """Base measures for one entity over ``period``, for an experiment's verdict.

        Which tables an entity can reach depends on its level: the store knows nothing
        about which ad was clicked, and the web funnel is only attributable per session
        source. A metric the entity cannot carry comes back missing, and FR-10.3 then
        says inconclusive rather than guessing.
        """
        totals = Totals()
        if level != "source":
            totals = totals.merge(self._ad_totals(period, level, key))
        if level == "account":
            totals = totals.merge(self._store_totals(period))
        sources = _web_sources(level, key)
        if sources is not None:
            totals = totals.merge(self._web_totals(period, sources))
        return totals

    def _ad_totals(self, period: Period, level: str, key: str) -> Totals:
        stmt = select(*(_sum(m) for m in AD_MEASURES), _days()).where(
            FactAdDaily.date.between(period.start, period.end)
        )
        for clause in _entity_filter(level, key):
            stmt = stmt.where(clause)
        return _totals(self._session.execute(stmt).mappings().one(), AD_MEASURES)

    def _store_totals(self, period: Period) -> Totals:
        stmt = select(
            func.sum(FactStoreDaily.orders).label("store_orders"),
            func.sum(FactStoreDaily.revenue).label("store_revenue"),
            _days(FactStoreDaily.date),
        ).where(FactStoreDaily.date.between(period.start, period.end))
        return _totals(self._session.execute(stmt).mappings().one(), STORE_SUMS)

    def _web_totals(self, period: Period, sources: tuple[str, ...]) -> Totals:
        sums = [func.sum(getattr(FactWebDaily, m)).label(m) for m in WEB_MEASURES]
        stmt = select(*sums, _days(FactWebDaily.date)).where(
            FactWebDaily.date.between(period.start, period.end)
        )
        if sources:
            stmt = stmt.where(FactWebDaily.source.in_(sources))
        return _totals(self._session.execute(stmt).mappings().one(), WEB_MEASURES)

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


def _days(column: Any = FactAdDaily.date) -> ColumnElement[Any]:
    """How many distinct days the rows cover, which is the sample behind the totals."""
    return func.count(column.distinct()).label("days")


def _totals(row: Any, measures: Sequence[str]) -> Totals:
    """One summed row as measures and coverage; a measure with no rows stays absent."""
    found = {measure: float(row[measure]) for measure in measures if row[measure] is not None}
    return Totals(found, int(row["days"] or 0))


def _entity_filter(level: str, key: str) -> list[ColumnElement[bool]]:
    """The ad-fact conditions that isolate one entity; the account needs none."""
    column = _ENTITY_KEYS.get(level)
    if column is not None:
        return [column == (int(key) if level in _NUMERIC_LEVELS else key)]
    if level == "age_group":
        # A segment's key carries its ad set, because the label alone repeats across them.
        ad_set, _, age_group = key.partition("|")
        return [FactAdDaily.ad_set_id == int(ad_set), FactAdDaily.age_group == age_group]
    return []


def _web_sources(level: str, key: str) -> tuple[str, ...] | None:
    """The session sources this entity's funnel numbers come from, or ``None`` for neither.

    An empty tuple means every source, which is what an account-wide entity gets.
    """
    if level == "account":
        return ()
    if level == "source":
        return (key,)
    if level == "channel":
        found = tuple(source for source, channel in PAID_WEB_SOURCES.items() if channel == key)
        return found or None
    return None


def _sum(measure: str) -> ColumnElement[Any]:
    column = getattr(FactAdDaily, measure)
    if measure != "reach":
        return func.sum(column).label(measure)
    # Google reports no reach; a sum over only the Meta rows would inflate frequency.
    complete = func.count(column) == func.count()
    return case((complete, func.sum(column))).label(measure)
