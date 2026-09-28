"""One investigated opportunity as a database row.

The evidence, the diagnosis and the recommendation are stored whole as JSONB, so this
is where the domain dataclasses become plain JSON: dates as ISO strings, decimals as
floats, tuples as lists. Read back by ``services/opportunities.py``.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from mdia.domain.opportunities import first_seen

if TYPE_CHECKING:
    from mdia.agents.investigation import Investigation
    from mdia.domain.evidence import Evidence
    from mdia.domain.opportunities import Opportunity
    from mdia.domain.recommendations import Recommendation


def opportunity_row(
    run_id: int,
    opportunity: Opportunity,
    seen: tuple[dt.date, dt.date] | None,
    result: Investigation,
) -> dict[str, Any]:
    """The upsert payload for one opportunity, keyed so a re-run updates it in place."""
    entity = opportunity.entity
    window = opportunity.window
    return {
        "key": opportunity.key,
        "analysis_run_id": run_id,
        "kind": opportunity.kind,
        "entity_level": entity.level,
        "entity_key": entity.key,
        "entity_name": entity.name,
        "channel_id": entity.channel,
        "window_start": window.start,
        "window_end": window.end,
        "first_seen_date": first_seen(window, seen),
        "last_seen_date": window.end,
        "primary_metric": opportunity.primary.metric,
        "primary_detector": opportunity.primary.detector,
        "impact": opportunity.impact,
        "score": opportunity.score,
        "signals": [_jsonable(asdict(signal)) for signal in opportunity.signals],
        "evidence": _evidence(result.evidence),
        "diagnosis": _diagnosis(result),
        "recommendation": _recommendation(result.recommendation),
        "confidence": result.confidence,
        "priority": result.priority,
        "diagnosis_source": result.source,
    }


def _evidence(evidence: Evidence) -> dict[str, Any]:
    """The evidence tree and its context; the signals have a column of their own."""
    row = {
        "tree": asdict(evidence.tree),
        "trust": evidence.trust,
        "protected": evidence.protected,
        "impact": evidence.impact,
        "signal_ids": list(evidence.signal_ids),
    }
    return {key: _jsonable(value) for key, value in row.items()}


def _diagnosis(result: Investigation) -> dict[str, Any]:
    diagnosis = result.diagnosis
    row = {
        "observation": diagnosis.observation,
        "hypotheses": [asdict(hypothesis) for hypothesis in diagnosis.hypotheses],
        "alternatives": list(diagnosis.alternatives),
        "source": result.source,
    }
    return {key: _jsonable(value) for key, value in row.items()}


def _recommendation(recommendation: Recommendation | None) -> dict[str, Any] | None:
    return None if recommendation is None else _jsonable(asdict(recommendation))


def _jsonable(value: Any) -> Any:
    """Dates and decimals as JSON, for the JSONB columns."""
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value
