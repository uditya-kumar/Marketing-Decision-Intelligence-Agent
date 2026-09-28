"""The decision log: one row per human call, read back with the chain behind it (FR-10.4)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from mdia.models import Decision, Experiment, Opportunity

if TYPE_CHECKING:
    from collections.abc import Sequence
    from decimal import Decimal

    from sqlalchemy.orm import Session

    from mdia.models.experiments import DecisionKind

# Opportunity → experiment → outcome, as the timeline shows it.
type Chain = tuple[Decision, Opportunity, Experiment | None]


class DecisionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def log(
        self,
        kind: DecisionKind,
        *,
        opportunity_id: int,
        experiment_id: int | None = None,
        reason: str | None = None,
        impact: Decimal | float | None = None,
    ) -> Decision:
        decision = Decision(
            kind=kind,
            opportunity_id=opportunity_id,
            experiment_id=experiment_id,
            reason=reason,
            impact=impact,
        )
        self._session.add(decision)
        self._session.flush()
        return decision

    def list(self, limit: int = 200) -> Sequence[Chain]:
        """Every decision, newest first, with its opportunity and any experiment it made."""
        stmt = (
            select(Decision, Opportunity, Experiment)
            .join(Opportunity, Opportunity.id == Decision.opportunity_id)
            .outerjoin(Experiment, Experiment.id == Decision.experiment_id)
            .order_by(Decision.created_at.desc(), Decision.id.desc())
            .limit(limit)
        )
        rows = self._session.execute(stmt)
        return [(decision, opportunity, experiment) for decision, opportunity, experiment in rows]
