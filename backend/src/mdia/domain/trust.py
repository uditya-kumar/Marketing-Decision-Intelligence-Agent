"""Data trust (FR-3.5, FR-5): can today's numbers be relied on?"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mdia.domain.sources import SOURCES

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Iterable, Mapping

    from mdia.domain.sources import Source


def as_of_date(
    latest_by_source: Mapping[Source, dt.date | None],
    required: Iterable[Source] = SOURCES,
) -> dt.date | None:
    """Return the earliest of the required sources' latest dates.

    Anything later is missing at least one source, so blended metrics such as MER
    would be wrong for it. ``None`` until every required source has some data.
    """
    latest = [latest_by_source.get(source) for source in required]
    if any(day is None for day in latest):
        return None
    return min(day for day in latest if day is not None)


def missing_sources(
    latest_by_source: Mapping[Source, dt.date | None],
    required: Iterable[Source] = SOURCES,
) -> list[Source]:
    return [source for source in required if latest_by_source.get(source) is None]
