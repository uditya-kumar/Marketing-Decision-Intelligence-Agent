"""Grounding violations, before and after the guard (FR-13.4).

Every call to the model is logged, one row per attempt, so the guard can be measured
from both sides: how often the model said something the evidence did not support, and
how often that survived into an answer a user could read. The second number is the one
§13 sets to zero — a violation the guard caught and replaced is the system working.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mdia.agents.llm import CallRecord
from mdia.models.llm import LlmCall
from sqlalchemy import select

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sqlalchemy.orm import Session

# §13: no ungrounded number ever reaches a user.
TARGET_LEAKED = 0


@dataclass(frozen=True, slots=True)
class GroundingScore:
    """FR-13.4 over a set of logged calls."""

    calls: list[CallRecord]

    @property
    def attempts(self) -> int:
        return len(self.calls)

    @property
    def answers(self) -> int:
        """Answers asked for: one per first attempt, retries belonging to the same one."""
        return sum(1 for call in self.calls if call.attempt == 1)

    @property
    def ungrounded(self) -> int:
        """Attempts the guard rejected, whether or not the retry then succeeded."""
        return sum(1 for call in self.calls if not call.grounded and call.error is None)

    @property
    def errors(self) -> int:
        """Attempts that never produced a parsable answer: transport or schema failures."""
        return sum(1 for call in self.calls if call.error is not None)

    @property
    def fell_back(self) -> int:
        """Answers that ended rule-based, because no attempt of theirs was grounded."""
        return sum(1 for call in self.calls if call.attempt == 1 and call.fallback)

    @property
    def recovered(self) -> int:
        """Answers a retry saved: the guard fired, the second try was grounded."""
        return sum(1 for call in self.calls if call.attempt > 1 and call.grounded)

    @property
    def leaked(self) -> int:
        """Ungrounded answers shown to a user. Zero by construction, reported to prove it."""
        return sum(1 for call in self.calls if call.grounded and call.fallback)

    @property
    def violation_rate(self) -> float:
        """Before the guard: the share of attempts it had to reject."""
        return _ratio(self.ungrounded, self.attempts)

    @property
    def fallback_rate(self) -> float:
        """After the guard: the share of answers that came out rule-based instead."""
        return _ratio(self.fell_back, self.answers)

    @property
    def retries(self) -> int:
        return sum(1 for call in self.calls if call.attempt > 1)

    def by_purpose(self) -> dict[str, GroundingScore]:
        grouped: dict[str, list[CallRecord]] = {}
        for call in self.calls:
            grouped.setdefault(call.purpose, []).append(call)
        return {purpose: GroundingScore(calls) for purpose, calls in sorted(grouped.items())}


def score(calls: Iterable[CallRecord]) -> GroundingScore:
    return GroundingScore(list(calls))


def from_db(session: Session, *, purpose: str | None = None) -> GroundingScore:
    """Score what a running backend logged (NFR-3), the table's own rows unchanged."""
    query = select(LlmCall).order_by(LlmCall.id)
    if purpose is not None:
        query = query.where(LlmCall.purpose == purpose)
    return score(_record(row) for row in session.scalars(query))


def _record(row: LlmCall) -> CallRecord:
    return CallRecord(
        purpose=row.purpose,
        provider=row.provider,
        model=row.model,
        prompt_version=row.prompt_version,
        attempt=row.attempt,
        latency_ms=row.latency_ms,
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        grounded=row.grounded,
        fallback=row.fallback,
        error=row.error,
    )


def _ratio(part: int, whole: int) -> float:
    return 0.0 if whole == 0 else part / whole
