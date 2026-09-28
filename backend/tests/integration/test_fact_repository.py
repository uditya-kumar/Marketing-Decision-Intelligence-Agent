"""2.2: loading the same export twice leaves every table unchanged."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import func, select

from mdia.ingestion.reader import read_csv
from mdia.models import (
    DimAdSet,
    DimCampaign,
    DimChannel,
    DimCreative,
    FactAdDaily,
    FactStoreDaily,
    FactWebDaily,
)
from mdia.repositories.facts import FactRepository

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from mdia.db.base import Base

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "csv"
TABLES: tuple[type[Base], ...] = (
    DimChannel,
    DimCampaign,
    DimAdSet,
    DimCreative,
    FactAdDaily,
    FactWebDaily,
    FactStoreDaily,
)

pytestmark = pytest.mark.integration


def _load(session: Session, file_name: str) -> None:
    batch = read_csv((FIXTURES / file_name).read_bytes())
    facts = FactRepository(session)
    if batch.template.kind == "ad":
        facts.upsert_ad_records(batch.records, batch.template.label)
    elif batch.template.kind == "web":
        facts.upsert_web_records(batch.records)
    else:
        facts.upsert_store_records(batch.records)
    session.commit()


def _counts(session: Session) -> dict[str, int]:
    return {
        model.__tablename__: session.scalar(select(func.count()).select_from(model)) or 0
        for model in TABLES
    }


def test_loading_the_same_files_twice_gives_the_same_row_counts(db_session: Session) -> None:
    files = sorted(path.name for path in FIXTURES.glob("*.csv"))
    for name in files:
        _load(db_session, name)
    first = _counts(db_session)
    for name in files:
        _load(db_session, name)

    assert _counts(db_session) == first
    assert first == {
        "dim_channel": 2,
        "dim_campaign": 2,
        "dim_ad_set": 2,
        "dim_creative": 2,
        "fact_ad_daily": 16,
        "fact_web_daily": 8,
        "fact_store_daily": 2,
    }


def test_reloading_a_corrected_row_updates_it_in_place(db_session: Session) -> None:
    original = (FIXTURES / "store_orders.csv").read_text(encoding="utf-8")
    header, first_row, *rest = original.splitlines()
    cells = first_row.split(",")
    cells[1] = "123"  # Orders
    corrected = "\n".join([header, ",".join(cells), *rest])
    _load(db_session, "store_orders.csv")

    facts = FactRepository(db_session)
    facts.upsert_store_records(read_csv(corrected).records)
    db_session.commit()

    first_day = select(FactStoreDaily.orders).order_by(FactStoreDaily.date).limit(1)
    assert db_session.scalar(first_day) == 123
    assert db_session.scalar(select(func.count()).select_from(FactStoreDaily)) == 2
    revenue = db_session.scalar(select(func.sum(FactStoreDaily.revenue)))
    assert isinstance(revenue, Decimal)
