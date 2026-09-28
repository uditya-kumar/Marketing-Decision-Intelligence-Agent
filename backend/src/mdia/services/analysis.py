"""The analysis run (FR-6.4): sweep the detectors over the latest data and store the result.

Runs as a background task after an upload, so it owns its own session and never
lets a failure escape into the request that started it.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pandas as pd
import structlog

from mdia.agents.investigation import build_investigation, investigate
from mdia.agents.llm import get_chat_model
from mdia.db.session import session_scope
from mdia.domain.detection import Context, Facts, analyse
from mdia.domain.periods import Period, month_to_date, trailing
from mdia.domain.signals import BASELINE_DAYS, WINDOW_DAYS
from mdia.domain.sources import CHANNELS
from mdia.domain.trust import worst
from mdia.repositories.analysis import AnalysisRepository
from mdia.repositories.facts import AD_MEASURES, FactRepository
from mdia.repositories.llm_calls import LlmCallRepository
from mdia.repositories.metrics import WEB_MEASURES, MetricsRepository
from mdia.repositories.settings import SettingsRepository
from mdia.services.experiments import ExperimentService
from mdia.services.metrics import STORE_MEASURES, account_targets
from mdia.services.opportunity_rows import opportunity_row
from mdia.services.trust import TrustService

if TYPE_CHECKING:
    from collections.abc import Sequence

    from langchain_core.language_models import BaseChatModel
    from sqlalchemy.orm import Session

    from mdia.agents.investigation import Investigation
    from mdia.domain.opportunities import Opportunity
    from mdia.domain.sources import Channel
    from mdia.domain.trust import TrackingCheck, TrustStatus
    from mdia.models import AnalysisRun, BusinessSettings
    from mdia.models.analysis import AnalysisStatus
    from mdia.services.trust import TrustView

log = structlog.get_logger(__name__)

# How many opportunities are worth an LLM call; the rest are diagnosed by the rules,
# which every opportunity gets anyway (FR-8.3's fallback is also the default).
INVESTIGATE_TOP_N = 5

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
        self._llm_calls = LlmCallRepository(session)
        self._experiments = ExperimentService(session)

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
            investigated = self._investigate(found, trust)
            self._store(run.id, found, investigated)
            # After storing, so an experiment's verdict has the last word on its
            # opportunity's status (FR-10.3).
            self._experiments.evaluate_due(as_of, run.id)
            self._analysis.finish(
                run.id,
                status="done",
                signals=sum(len(o.signals) for o in found),
                opportunities=len(found),
                llm=sum(1 for result in investigated if result.source == "llm"),
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

    def _investigate(self, found: Sequence[Opportunity], trust: TrustView) -> list[Investigation]:
        """Diagnose every opportunity, one after another; the strongest few get the LLM.

        Two graphs, because the rest are worth a rule-based diagnosis but not a call:
        an LLM answer that only re-words the same evidence is not worth the latency.
        """
        protected = _protected(self._settings.get())
        statuses = _trust_statuses(trust)
        with_llm = build_investigation(_model())
        rules_only = build_investigation(None)
        results = []
        for index, opportunity in enumerate(found):
            channel = opportunity.entity.channel
            results.append(
                investigate(
                    with_llm if index < INVESTIGATE_TOP_N else rules_only,
                    opportunity,
                    # A blended entity is only as trustworthy as its worst channel.
                    trust=statuses.get(channel, "ok") if channel else worst(statuses.values()),
                    protected=protected,
                )
            )
        return results

    def _store(
        self,
        run_id: int,
        found: Sequence[Opportunity],
        investigated: Sequence[Investigation],
    ) -> None:
        seen = self._analysis.seen_dates([o.key for o in found])
        rows = [
            opportunity_row(run_id, o, seen.get(o.key), result)
            for o, result in zip(found, investigated, strict=True)
        ]
        self._analysis.save(run_id, rows)
        for result in investigated:
            self._llm_calls.log(result.calls, analysis_run_id=run_id)


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


def _model() -> BaseChatModel | None:
    """The chat model, or ``None`` when it cannot even be built (NFR-5)."""
    try:
        return get_chat_model()
    except Exception as error:
        log.warning("llm.unavailable", error=str(error))
        return None


def _trust_statuses(trust: TrustView) -> dict[Channel, TrustStatus]:
    return {source.source: source.status for source in trust.sources if source.source in CHANNELS}


def _protected(settings: BusinessSettings | None) -> list[str]:
    return [
        str(campaign_id) for campaign_id in (settings.protected_campaign_ids if settings else [])
    ]
