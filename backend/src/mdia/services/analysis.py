"""The analysis run (FR-6.4): sweep the detectors over the latest data and store the result.

Runs as a background task after an upload, so it owns its own session and never
lets a failure escape into the request that started it.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pandas as pd
import structlog

from mdia.db.session import session_scope
from mdia.domain.detection import Context, Facts, analyse
from mdia.domain.opportunities import first_seen
from mdia.domain.periods import Period, month_to_date, trailing
from mdia.domain.signals import BASELINE_DAYS, WINDOW_DAYS
from mdia.domain.sources import CHANNELS
from mdia.repositories.analysis import AnalysisRepository
from mdia.repositories.facts import AD_MEASURES, FactRepository
from mdia.repositories.metrics import WEB_MEASURES, MetricsRepository
from mdia.repositories.settings import SettingsRepository
from mdia.services.metrics import STORE_MEASURES, account_targets
from mdia.services.trust import TrustService

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.orm import Session

    from mdia.domain.opportunities import Opportunity
    from mdia.domain.sources import Channel
    from mdia.domain.trust import TrackingCheck
    from mdia.models import AnalysisRun, BusinessSettings
    from mdia.models.analysis import AnalysisStatus
    from mdia.services.trust import TrustView

log = structlog.get_logger(__name__)

_AD_COLUMNS = (
    "date",
    "channel_id",
    "campaign_id",
    "campaign_name",
    "ad_set_id",
    "ad_set_name",
    "creative_id",
    "creative_name",
    "age_group",
    *AD_MEASURES,
)


@dataclass(frozen=True, slots=True)
class AnalysisStatusView:
    status: AnalysisStatus | None
    as_of_date: dt.date | None
    signal_count: int
    opportunity_count: int
    started_at: dt.datetime | None
    finished_at: dt.datetime | None
    error: str | None


class AnalysisService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._analysis = AnalysisRepository(session)
        self._facts = FactRepository(session)
        self._metrics = MetricsRepository(session)
        self._settings = SettingsRepository(session)
        self._trust = TrustService(session)

    def status(self) -> AnalysisStatusView:
        run = self._analysis.latest_run()
        if run is None:
            return AnalysisStatusView(None, None, 0, 0, None, None, None)
        return AnalysisStatusView(
            run.status,
            run.as_of_date,
            run.signal_count,
            run.opportunity_count,
            run.started_at,
            run.finished_at,
            run.error,
        )

    def run(self) -> AnalysisRun | None:
        """Detect, score, group and store. ``None`` when there is nothing to analyse yet."""
        trust = self._trust.check(self._facts.coverage())
        as_of = trust.as_of_date
        if as_of is None:
            return None
        run = self._analysis.start(as_of)
        # Committed on its own so the UI can show "Analysing…" while the sweep runs.
        self._session.commit()
        try:
            found = self._analyse(as_of, trust)
            self._store(run.id, found)
            self._analysis.finish(
                run.id,
                status="done",
                signals=sum(len(o.signals) for o in found),
                opportunities=len(found),
            )
            self._session.commit()
        except Exception as error:
            self._session.rollback()
            self._analysis.finish(run.id, status="failed", error=str(error)[:500])
            self._session.commit()
            raise
        return run

    def _analyse(self, as_of: dt.date, trust: TrustView) -> list[Opportunity]:
        settings = self._settings.get()
        window = trailing(as_of, WINDOW_DAYS)
        baseline = trailing(window.start - dt.timedelta(days=1), BASELINE_DAYS)
        # Pacing needs the whole month; everything else needs the baseline.
        span = Period(min(baseline.start, month_to_date(as_of).start), as_of)
        facts = Facts(
            ads=_frame(self._metrics.entity_daily(span), _AD_COLUMNS, AD_MEASURES),
            web=_frame(
                self._metrics.web_daily(span), ("date", "source", *WEB_MEASURES), WEB_MEASURES
            ),
            store=_frame(
                self._metrics.store_daily(span), ("date", *STORE_MEASURES), STORE_MEASURES
            ),
        )
        context = Context(
            as_of=as_of,
            targets=account_targets(settings, as_of),
            month_budgets=_budgets(settings),
            festive=_festive(settings),
            broken=_broken(trust),
            tracking=_tracking(trust),
        )
        return analyse(facts, context)

    def _store(self, run_id: int, found: Sequence[Opportunity]) -> None:
        seen = self._analysis.seen_dates([o.key for o in found])
        rows = [_row(run_id, o, seen.get(o.key)) for o in found]
        self._analysis.save(run_id, rows)


def run_analysis() -> None:
    """Background-task entry point: a session of its own, and no exception escapes."""
    try:
        with session_scope() as session:
            run = AnalysisService(session).run()
        log.info("analysis.finished", run_id=run.id if run else None)
    except Exception:
        log.exception("analysis.failed")


def _frame(
    rows: list[dict[str, Any]], columns: Sequence[str], measures: Sequence[str]
) -> pd.DataFrame:
    """Rows as a frame with float measures: Postgres returns ``Decimal`` and ``None``."""
    frame = pd.DataFrame(rows, columns=list(columns))
    frame[list(measures)] = frame[list(measures)].astype(float)
    return frame


def _budgets(settings: BusinessSettings | None) -> dict[Channel, float]:
    budgets = settings.monthly_budgets if settings else {}
    return {channel: float(budgets[channel]) for channel in CHANNELS if budgets.get(channel)}


def _festive(settings: BusinessSettings | None) -> list[Period]:
    windows = settings.festive_windows if settings else []
    return [
        Period(dt.date.fromisoformat(window["start"]), dt.date.fromisoformat(window["end"]))
        for window in windows or []
    ]


def _broken(trust: TrustView) -> list[Channel]:
    return [
        source.source
        for source in trust.sources
        if source.source in CHANNELS and source.tracking and source.tracking.status == "broken"
    ]


def _tracking(trust: TrustView) -> dict[Channel, TrackingCheck]:
    return {
        source.source: source.tracking
        for source in trust.sources
        if source.source in CHANNELS and source.tracking
    }


def _row(
    run_id: int, opportunity: Opportunity, seen: tuple[dt.date, dt.date] | None
) -> dict[str, Any]:
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
    }


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
