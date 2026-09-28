"""Business settings (FR-1): a single row of goals, economics and guardrails."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mdia.db.base import Base

MONEY = Numeric(14, 2)


class BusinessSettings(Base):
    __tablename__ = "settings"
    # One company per install, so the row is pinned to id 1.
    __table_args__ = (CheckConstraint("id = 1", name="single_row"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False, default=1)
    business_name: Mapped[str] = mapped_column(String(128))
    gross_margin_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    target_cpa: Mapped[Decimal | None] = mapped_column(MONEY)
    target_roas: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    monthly_revenue_goal: Mapped[Decimal | None] = mapped_column(MONEY)
    # {channel: rupees per month}
    monthly_budgets: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # [{name, start, end}] with ISO dates
    festive_windows: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    protected_campaign_ids: Mapped[list[int]] = mapped_column(JSONB)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
