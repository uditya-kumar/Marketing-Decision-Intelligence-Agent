"""The weekly report (FR-11): gather the week, narrate it, store it, read it back.

Nothing is recomputed for the report. The KPIs, pacing, opportunities, decisions and
verdicts all come from the services the screens use, so the report can never disagree
with what the team saw during the week.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

from mdia.agents.llm import get_chat_model
from mdia.agents.report import build_report, write_report
from mdia.core.errors import NotFoundError, ValidationError
from mdia.domain.periods import trailing
from mdia.domain.trust import unreliable_metrics
from mdia.repositories.facts import FactRepository
from mdia.repositories.llm_calls import LlmCallRepository
from mdia.repositories.reports import ReportRepository
from mdia.repositories.settings import SettingsRepository
from mdia.services.decisions import DecisionService
from mdia.services.experiments import ExperimentService
from mdia.services.metrics import COMPARE_DAYS, MetricsService
from mdia.services.opportunities import OpportunityService
from mdia.services.pacing import PacingService
from mdia.services.report_rows import payload_for, report_row
from mdia.services.trust import TrustService

if TYPE_CHECKING:
    import datetime as dt

    from langchain_core.language_models import BaseChatModel
    from sqlalchemy.orm import Session

    from mdia.domain.periods import Period
    from mdia.domain.reports import WeeklyPayload
    from mdia.models import WeeklyReport
    from mdia.models.reports import ReportSource
    from mdia.services.decisions import DecisionView
    from mdia.services.experiment_rows import ExperimentView
    from mdia.services.opportunities import OpportunitySummary

log = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ReportView:
    """One stored report as the Reports screen reads it (UI.md §5.6)."""

    id: int
    week: Period
    summary: list[str]
    detail: list[str]
    source: ReportSource
    grounded: bool
    created_at: dt.datetime


@dataclass(frozen=True, slots=True)
class ReportsView:
    """The history, plus the week a fresh report would cover."""

    reports: list[ReportView]
    next_week_end: dt.date | None


class ReportService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._reports = ReportRepository(session)
        self._settings = SettingsRepository(session)
        self._facts = FactRepository(session)
        self._llm_calls = LlmCallRepository(session)
        self._metrics = MetricsService(session)
        self._trust = TrustService(session)
        self._pacing = PacingService(session)
        self._opportunities = OpportunityService(session)
        self._decisions = DecisionService(session)
        self._experiments = ExperimentService(session)

    def find(self) -> ReportsView:
        rows = [_view(row) for row in self._reports.list()]
        return ReportsView(rows, self._metrics.as_of())

    def get(self, report_id: int) -> ReportView:
        row = self._reports.get(report_id)
        if row is None:
            raise NotFoundError(f"No report {report_id}.")
        return _view(row)

    def generate(self, week_end: dt.date | None = None) -> ReportView:
        """Build the week's payload, narrate it, and store it under that week (FR-11).

        Generating the same week twice replaces it: the facts may have changed with a
        re-upload, and a week has one report.
        """
        end = week_end or self._metrics.as_of()
        if end is None:
            raise ValidationError("There is no data yet to report on.")
        week = trailing(end, COMPARE_DAYS)
        payload = self._payload(week)
        report = write_report(build_report(_model()), payload)
        saved = self._reports.save(report_row(payload, report))
        self._llm_calls.log(report.calls)
        self._session.commit()
        log.info("report.generated", week_end=str(end), source=report.source)
        return _view(saved)

    def _payload(self, week: Period) -> WeeklyPayload:
        settings = self._settings.get()
        trust = self._trust.check(self._facts.coverage())
        kpis = self._metrics.today(week.end, settings, unreliable_metrics(trust.sources))
        budgets = settings.monthly_budgets if settings else {}
        return payload_for(
            week,
            kpis=kpis.kpis,
            pacing=self._pacing.month(week.end, budgets or {}),
            opportunities=self._in_week(week),
            decisions=self._decided_in(week),
            experiments=self._watched_in(week),
        )

    def _in_week(self, week: Period) -> list[OpportunitySummary]:
        """The opportunities this week's analysis found, whatever has since been decided."""
        return [row for row in self._opportunities.find() if row.window.end in week]

    def _decided_in(self, week: Period) -> list[DecisionView]:
        return [row for row in self._decisions.find() if row.at.date() in week]

    def _watched_in(self, week: Period) -> list[ExperimentView]:
        """What the week can say about the changes: its verdicts, and what is still running."""
        return [
            row
            for row in self._experiments.find()
            if (row.evaluated_on is not None and row.evaluated_on in week)
            or row.status == "running"
        ]


def _view(row: WeeklyReport) -> ReportView:
    narrative = row.narrative or {}
    return ReportView(
        id=row.id,
        week=trailing(row.week_end, (row.week_end - row.week_start).days + 1),
        summary=list(narrative.get("summary") or []),
        detail=list(narrative.get("detail") or []),
        source=row.source,
        grounded=row.grounded,
        created_at=row.created_at,
    )


def _model() -> BaseChatModel | None:
    """The chat model, or ``None`` when it cannot even be built (NFR-5)."""
    try:
        return get_chat_model()
    except Exception as error:
        log.warning("llm.unavailable", error=str(error))
        return None
