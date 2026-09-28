"""Every call to a language model, logged (NFR-3).

One row per call, not per investigation, so a retry after a grounding failure is
visible as its own attempt. That is what the grounding report (FR-13.4) counts: the
violation rate before the guard is the share of attempts that were not grounded, and
the rate after it is the share of investigations that ended in the fallback.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from mdia.db.base import Base


class LlmCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Which graph asked: "diagnosis" or "report".
    purpose: Mapped[str] = mapped_column(String(32))
    analysis_run_id: Mapped[int | None] = mapped_column(ForeignKey("analysis_runs.id"))
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(128))
    prompt_version: Mapped[str] = mapped_column(String(32))
    attempt: Mapped[int] = mapped_column(default=1)
    latency_ms: Mapped[int] = mapped_column(default=0)
    input_tokens: Mapped[int | None] = mapped_column()
    output_tokens: Mapped[int | None] = mapped_column()
    grounded: Mapped[bool] = mapped_column(default=False)
    fallback: Mapped[bool] = mapped_column(default=False)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
