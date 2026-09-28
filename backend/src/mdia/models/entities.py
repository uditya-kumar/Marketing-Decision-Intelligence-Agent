"""Ad entity dimensions: channel → campaign → ad set → creative.

Platform IDs are kept as ``external_id`` (unique within the parent) so re-uploads map
to the same rows; facts reference the surrogate integer IDs.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from mdia.db.base import Base


class DimChannel(Base):
    __tablename__ = "dim_channel"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))


class DimCampaign(Base):
    __tablename__ = "dim_campaign"
    __table_args__ = (UniqueConstraint("channel_id", "external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[str] = mapped_column(ForeignKey("dim_channel.id"))
    external_id: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(255))
    # Meta campaigns run on one publisher platform (facebook | instagram).
    platform: Mapped[str | None] = mapped_column(String(32))


class DimAdSet(Base):
    __tablename__ = "dim_ad_set"
    __table_args__ = (UniqueConstraint("campaign_id", "external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("dim_campaign.id"))
    external_id: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(255))


class DimCreative(Base):
    __tablename__ = "dim_creative"
    __table_args__ = (UniqueConstraint("ad_set_id", "external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ad_set_id: Mapped[int] = mapped_column(ForeignKey("dim_ad_set.id"))
    external_id: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(255))
