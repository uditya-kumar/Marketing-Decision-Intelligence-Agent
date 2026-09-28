"""The LLM call log: writes from the analysis, and the counts the evaluation reads."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

from mdia.models import LlmCall

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.orm import Session

    from mdia.agents.llm import CallRecord


class LlmCallRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def log(self, records: Sequence[CallRecord], *, analysis_run_id: int | None = None) -> None:
        self._session.add_all(
            LlmCall(**asdict(record), analysis_run_id=analysis_run_id) for record in records
        )
