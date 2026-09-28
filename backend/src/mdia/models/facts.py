"""Daily fact tables, one per source family.

Each primary key is the source's natural key, which is what makes re-uploads
idempotent (``INSERT … ON CONFLICT`` on the key). Only base measures are stored;
ratios such as CTR or bounce rate are always recomputed from them.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from mdia.db.base import Base

MONEY = Numeric(14, 2)


class FactAdDaily(Base):
    """Platform-reported delivery per day × creative × age × device × region."""

    __tablename__ = "fact_ad_daily"
    __table_args__ = (
        Index("ix_fact_ad_daily_channel_date", "channel_id", "date"),
        Index("ix_fact_ad_daily_campaign_date", "campaign_id", "date"),
    )

    date: Mapped[dt.date] = mapped_column(primary_key=True)
    creative_id: Mapped[int] = mapped_column(ForeignKey("dim_creative.id"), primary_key=True)
    age_group: Mapped[str] = mapped_column(String(16), primary_key=True)
    device: Mapped[str] = mapped_column(String(16), primary_key=True)
    region: Mapped[str] = mapped_column(String(64), primary_key=True)
    # Denormalised parents so slice queries don't need to walk the entity tree.
    channel_id: Mapped[str] = mapped_column(ForeignKey("dim_channel.id"))
    campaign_id: Mapped[int] = mapped_column(ForeignKey("dim_campaign.id"))
    ad_set_id: Mapped[int] = mapped_column(ForeignKey("dim_ad_set.id"))
    impressions: Mapped[int]
    # Google Ads exports don't report reach.
    reach: Mapped[int | None]
    clicks: Mapped[int]
    spend: Mapped[Decimal] = mapped_column(MONEY)
    # Data-driven attribution reports fractional conversions.
    platform_conversions: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    platform_revenue: Mapped[Decimal] = mapped_column(MONEY)


class FactWebDaily(Base):
    """Web analytics per day × session source / medium × device."""

    __tablename__ = "fact_web_daily"

    date: Mapped[dt.date] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(128), primary_key=True)
    device: Mapped[str] = mapped_column(String(16), primary_key=True)
    sessions: Mapped[int]
    # GA4 has no bounce count; a bounce is a session that was not engaged.
    bounces: Mapped[int]
    add_to_cart: Mapped[int]
    checkout: Mapped[int]
    purchases: Mapped[int]
    revenue: Mapped[Decimal] = mapped_column(MONEY)


class FactStoreDaily(Base):
    """Store (order system) totals per day; the source of truth for orders and revenue."""

    __tablename__ = "fact_store_daily"

    date: Mapped[dt.date] = mapped_column(primary_key=True)
    orders: Mapped[int]
    # Net sales: gross sales less discounts and returns.
    revenue: Mapped[Decimal] = mapped_column(MONEY)
    discounts: Mapped[Decimal] = mapped_column(MONEY)
    refunds: Mapped[Decimal] = mapped_column(MONEY)
    new_customers: Mapped[int]
