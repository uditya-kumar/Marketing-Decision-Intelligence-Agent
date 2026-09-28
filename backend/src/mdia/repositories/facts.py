"""Daily fact tables: idempotent loads and per-source coverage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, literal, select, union_all

from mdia.models import FactAdDaily, FactStoreDaily, FactWebDaily
from mdia.repositories.entities import EntityRepository
from mdia.repositories.upsert import upsert

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Callable, Hashable, Mapping, Sequence

    from sqlalchemy import Select
    from sqlalchemy.orm import Session

    from mdia.domain.periods import Period
    from mdia.domain.sources import Source

type Row = Mapping[str, Any]

AD_MEASURES = (
    "impressions",
    "reach",
    "clicks",
    "spend",
    "platform_conversions",
    "platform_revenue",
)


@dataclass(frozen=True, slots=True)
class SourceCoverage:
    source: Source
    first_date: dt.date | None
    last_date: dt.date | None
    rows: int
    days: int


class FactRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._entities = EntityRepository(session)

    def upsert_ad_records(self, records: Sequence[Row], channel_name: str) -> None:
        """Load ad records, creating or renaming their channel/campaign/ad set/creative."""
        if not records:
            return
        for channel_id in {record["channel_id"] for record in records}:
            self._entities.upsert_channel(channel_id, channel_name)
        campaigns = self._entities.upsert_campaigns(
            _unique(
                records,
                lambda r: (r["channel_id"], r["campaign_external_id"]),
                lambda r: {
                    "channel_id": r["channel_id"],
                    "external_id": r["campaign_external_id"],
                    "name": r["campaign_name"],
                    "platform": r["platform"],
                },
            )
        )

        def campaign_id(r: Row) -> int:
            return campaigns[(r["channel_id"], r["campaign_external_id"])]

        ad_sets = self._entities.upsert_ad_sets(
            _unique(
                records,
                lambda r: (campaign_id(r), r["ad_set_external_id"]),
                lambda r: {
                    "campaign_id": campaign_id(r),
                    "external_id": r["ad_set_external_id"],
                    "name": r["ad_set_name"],
                },
            )
        )

        def ad_set_id(r: Row) -> int:
            return ad_sets[(campaign_id(r), r["ad_set_external_id"])]

        creatives = self._entities.upsert_creatives(
            _unique(
                records,
                lambda r: (ad_set_id(r), r["creative_external_id"]),
                lambda r: {
                    "ad_set_id": ad_set_id(r),
                    "external_id": r["creative_external_id"],
                    "name": r["creative_name"],
                },
            )
        )
        facts = [
            {
                "date": r["date"],
                "channel_id": r["channel_id"],
                "campaign_id": campaign_id(r),
                "ad_set_id": ad_set_id(r),
                "creative_id": creatives[(ad_set_id(r), r["creative_external_id"])],
                "age_group": r["age_group"],
                "device": r["device"],
                "region": r["region"],
                **{measure: r[measure] for measure in AD_MEASURES},
            }
            for r in records
        ]
        upsert(self._session, FactAdDaily, facts)

    def upsert_web_records(self, records: Sequence[Row]) -> None:
        upsert(self._session, FactWebDaily, records)

    def upsert_store_records(self, records: Sequence[Row]) -> None:
        upsert(self._session, FactStoreDaily, records)

    def coverage(self) -> list[SourceCoverage]:
        """Date span and row count of each source that has any data."""
        # One round trip: dashboard latency is dominated by trips to the database.
        stmt = union_all(
            _coverage_query(FactAdDaily.date, FactAdDaily.channel_id),
            _coverage_query(FactWebDaily.date, literal("web_analytics")),
            _coverage_query(FactStoreDaily.date, literal("store_orders")),
        )
        found = [SourceCoverage(*row) for row in self._session.execute(stmt)]
        return [coverage for coverage in found if coverage.rows]

    def dates_by_source(self, period: Period) -> dict[Source, set[dt.date]]:
        """The days inside ``period`` that each source has any rows for."""
        stmt = union_all(
            _dates_query(FactAdDaily.date, FactAdDaily.channel_id, period),
            _dates_query(FactWebDaily.date, literal("web_analytics"), period),
            _dates_query(FactStoreDaily.date, literal("store_orders"), period),
        )
        dates: dict[Source, set[dt.date]] = {}
        for source, day in self._session.execute(stmt):
            dates.setdefault(source, set()).add(day)
        return dates


def _coverage_query(date_column: Any, source: Any) -> Select[Any]:
    stats = (
        func.min(date_column),
        func.max(date_column),
        func.count(),
        func.count(date_column.distinct()),
    )
    return select(source, *stats).group_by(source)


def _dates_query(date_column: Any, source: Any, period: Period) -> Select[Any]:
    return (
        select(source, date_column)
        .where(date_column.between(period.start, period.end))
        .group_by(source, date_column)
    )


def _unique(
    records: Sequence[Row],
    key: Callable[[Row], Hashable],
    build: Callable[[Row], dict[str, Any]],
) -> list[dict[str, Any]]:
    """One row per ``key``; later records win, so an entity takes its newest name."""
    return list({key(record): build(record) for record in records}.values())
