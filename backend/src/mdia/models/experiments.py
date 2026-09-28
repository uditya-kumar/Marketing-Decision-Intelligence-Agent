"""Experiments and the decision log (FR-10).

An experiment is the record of a change the team said they would make on the platform,
with the numbers it is judged on; a decision is the human act that created or ended one.
They are separate tables because a decision outlives the experiment it refers to: a
dismissal has no experiment at all.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Literal, get_args

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from mdia.db.base import Base
from mdia.models.analysis import SCORE, one_of

ExperimentStatus = Literal["draft", "running", "completed", "rejected"]
ExperimentVerdict = Literal["worked", "did_not_work", "inconclusive"]
DecisionKind = Literal["approve", "reject", "dismiss"]

# A metric value, not money: ROAS needs decimals, CPA needs rupees, both fit here.
VALUE = Numeric(16, 4)


class Experiment(Base):
    """One change under test, from the draft the recommendation filled in to its verdict."""

    __tablename__ = "experiments"
    __table_args__ = (
        one_of("status", get_args(ExperimentStatus)),
        one_of("verdict", get_args(ExperimentVerdict)),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"))
    action: Mapped[str] = mapped_column(String(32))
    hypothesis: Mapped[str] = mapped_column(Text)
    metric: Mapped[str] = mapped_column(String(32))
    baseline: Mapped[Decimal | None] = mapped_column(VALUE)
    target: Mapped[Decimal | None] = mapped_column(VALUE)
    duration_days: Mapped[int]
    status: Mapped[ExperimentStatus] = mapped_column(String(16), default="draft")
    # The last day of data at approval; the test is judged over the days after it.
    started_on: Mapped[dt.date | None]
    ends_on: Mapped[dt.date | None]
    # Filled in when a later upload covers the window (FR-10.3).
    before_value: Mapped[Decimal | None] = mapped_column(VALUE)
    after_value: Mapped[Decimal | None] = mapped_column(VALUE)
    sample_days: Mapped[int | None]
    verdict: Mapped[ExperimentVerdict | None] = mapped_column(String(16))
    evaluated_on: Mapped[dt.date | None]
    # Why it was rejected, if it was; an approval may carry a note too.
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Decision(Base):
    """One thing a person decided, kept forever so the log can show the chain (FR-10.4)."""

    __tablename__ = "decisions"
    __table_args__ = (one_of("kind", get_args(DecisionKind)),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[DecisionKind] = mapped_column(String(8))
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"))
    # A dismissal ends the opportunity without ever proposing a change.
    experiment_id: Mapped[int | None] = mapped_column(ForeignKey("experiments.id"))
    reason: Mapped[str | None] = mapped_column(Text)
    # What was at stake when the call was made, so the log needs no second query.
    impact: Mapped[Decimal | None] = mapped_column(SCORE)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
