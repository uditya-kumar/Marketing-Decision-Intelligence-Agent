"""CSV reader: source detection and row validation (tasks 2.3 and 2.4), no DB."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest

from mdia.core.errors import UnrecognisedFileError
from mdia.ingestion.reader import read_csv

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "csv"

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("file_name", "source", "rows"),
    [
        ("google_ads.csv", "google_ads", 8),
        ("meta_ads.csv", "meta_ads", 8),
        ("web_analytics.csv", "web_analytics", 8),
        ("store_orders.csv", "store_orders", 2),
    ],
)
def test_every_generator_export_is_recognised(file_name: str, source: str, rows: int) -> None:
    batch = read_csv((FIXTURES / file_name).read_bytes())

    assert batch.source == source
    assert (len(batch.records), batch.rejected) == (rows, [])
    assert batch.date_range == (dt.date(2026, 4, 18), dt.date(2026, 4, 19))


def test_validation_only_columns_are_dropped_and_derived_fields_added() -> None:
    web = read_csv((FIXTURES / "web_analytics.csv").read_bytes()).records[0]
    google = read_csv((FIXTURES / "google_ads.csv").read_bytes()).records[0]

    assert "engaged_sessions" not in web
    assert 0 <= web["bounces"] <= web["sessions"]
    assert "currency" not in google
    assert google["reach"] is None
    assert isinstance(google["spend"], Decimal)


def test_malformed_rows_are_reported_with_line_numbers_and_reasons() -> None:
    header, *rows = (FIXTURES / "google_ads.csv").read_text(encoding="utf-8").splitlines()
    rows[1] = rows[1].replace(",INR,", ",USD,")
    rows[4] = ",".join(cell if i != 13 else "lots" for i, cell in enumerate(rows[4].split(",")))
    rows.append(rows[0])

    batch = read_csv("\n".join([header, *rows]))

    assert len(batch.records) == 6
    assert [(r.line, r.errors[0].split(":")[0]) for r in batch.rejected] == [
        (3, "Currency code"),
        (6, "Clicks"),
        (10, "duplicate of line 2"),
    ]
    assert batch.rejected[1].values["Clicks"] == "lots"


def test_missing_columns_name_the_closest_export() -> None:
    header, *rows = (FIXTURES / "store_orders.csv").read_text(encoding="utf-8").splitlines()
    trimmed = header.replace(",New customers", "")

    with pytest.raises(UnrecognisedFileError, match=r"Store orders.*New customers"):
        read_csv("\n".join([trimmed, *rows]))


@pytest.mark.parametrize("content", [b"", b'{"not": "a csv"}', "Day,Orders".encode("utf-16")])
def test_unreadable_files_are_rejected(content: bytes) -> None:
    with pytest.raises(UnrecognisedFileError):
        read_csv(content)
