"""Turn a generator output directory into the frames the detection sweep expects.

The backend's own CSV reader does the parsing, so the harness sees exactly the rows
ingestion would have stored — without a database, which keeps a run reproducible
(NFR-2) and fast enough to sweep thresholds over a year of data.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any

import pandas as pd
from mdia.domain.detection import Facts
from mdia.domain.periods import Period
from mdia.ingestion.reader import read_csv
from mdia.repositories.facts import AD_MEASURES
from mdia.repositories.metrics import WEB_MEASURES
from mdia.services.metrics import STORE_MEASURES

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

    from mdia.ingestion.templates import Record, RecordKind

# Ad rows arrive keyed by the platform's own IDs, which is what ground truth names too.
_AD_IDS = {
    "campaign_external_id": "campaign_id",
    "ad_set_external_id": "ad_set_id",
    "creative_external_id": "creative_id",
}
_STORE_MEASURES = {"orders": "store_orders", "revenue": "store_revenue"}

# The detectors aggregate over device and region, so those columns are dropped here.
_GROUP_BY: dict[RecordKind, tuple[str, ...]] = {
    "ad": ("date", "channel_id", "campaign_id", "ad_set_id", "creative_id", "age_group"),
    "web": ("date", "source"),
    "store": ("date",),
}
_MEASURES: dict[RecordKind, tuple[str, ...]] = {
    "ad": AD_MEASURES,
    "web": WEB_MEASURES,
    "store": STORE_MEASURES,
}
_NAMES: dict[RecordKind, tuple[str, ...]] = {
    "ad": ("campaign_name", "ad_set_name", "creative_name"),
    "web": (),
    "store": (),
}


def load(directory: Path) -> Facts:
    """Read every export in ``directory`` and aggregate it to the detectors' grain."""
    records: dict[RecordKind, list[Record]] = {"ad": [], "web": [], "store": []}
    for path in sorted(directory.glob("*.csv")):
        batch = read_csv(path.read_bytes())
        records[batch.template.kind].extend(batch.records)
    return Facts(
        ads=_frame("ad", records["ad"], _AD_IDS),
        web=_frame("web", records["web"]),
        store=_frame("store", records["store"], _STORE_MEASURES),
    )


def span(facts: Facts) -> Period:
    """The days every frame covers, which is the widest window worth replaying."""
    starts: list[dt.date] = []
    ends: list[dt.date] = []
    for frame in (facts.ads, facts.web, facts.store):
        starts.append(min(frame["date"]))
        ends.append(max(frame["date"]))
    return Period(max(starts), min(ends))


def lineage(ads: pd.DataFrame) -> dict[str, tuple[str, ...]]:
    """Entity ID → its ancestors' IDs, so a scenario can be matched above its target."""
    columns = ["channel_id", "campaign_id", "ad_set_id", "creative_id"]
    levels = ("channel", "campaign", "ad_set", "creative")
    found: dict[str, tuple[str, ...]] = {}
    for row in ads[columns].drop_duplicates().to_dict("records"):
        ids = [f"{level}:{row[column]}" for level, column in zip(levels, columns, strict=True)]
        for depth, entity in enumerate(ids):
            found[entity] = tuple(ids[:depth])
    return found


def _frame(
    kind: RecordKind, records: Sequence[Record], rename: dict[str, str] | None = None
) -> pd.DataFrame:
    keys, measures, names = list(_GROUP_BY[kind]), list(_MEASURES[kind]), list(_NAMES[kind])
    frame = pd.DataFrame(records)
    if rename:
        frame = frame.rename(columns=rename)
    frame = _stringify(frame, (column for column in keys if column.endswith("_id")))
    frame[measures] = frame[measures].astype(float)
    # A name is a label, not a measure: keep one per entity rather than summing it.
    grouped = frame.groupby(keys, as_index=False, sort=False).agg(
        {**dict.fromkeys(measures, _total), **dict.fromkeys(names, "first")}
    )
    grouped["date"] = grouped["date"].map(_as_date)
    return grouped[keys + names + measures]


def _total(values: Any) -> float:
    """Sum that keeps an all-missing measure missing, as the repositories' SUM does."""
    return float(values.sum(min_count=1))


def _stringify(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    return frame.assign(**{column: frame[column].astype(str) for column in columns})


def _as_date(value: Any) -> dt.date:
    return value if isinstance(value, dt.date) else pd.Timestamp(value).date()
