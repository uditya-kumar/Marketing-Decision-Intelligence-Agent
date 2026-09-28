"""The Today screen: KPIs, data trust and pacing, sharing one read of coverage and settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mdia.domain.trust import unreliable_metrics
from mdia.repositories.analysis import AnalysisRepository
from mdia.repositories.facts import FactRepository
from mdia.repositories.settings import SettingsRepository
from mdia.services.experiments import ExperimentService
from mdia.services.metrics import MetricsService
from mdia.services.opportunities import OpportunityService
from mdia.services.pacing import PacingService
from mdia.services.trust import TrustService

if TYPE_CHECKING:
    import datetime as dt

    from sqlalchemy.orm import Session

    from mdia.domain.periods import Period
    from mdia.services.experiment_rows import ExperimentsToday
    from mdia.services.metrics import KpiSummary, TrendPoint
    from mdia.services.opportunities import OpportunitySummary
    from mdia.services.pacing import PacingView
    from mdia.services.trust import TrustView


@dataclass(frozen=True, slots=True)
class TodayView:
    as_of_date: dt.date | None
    configured: bool
    period: Period | None
    kpis: list[KpiSummary]
    trend: list[TrendPoint]
    trust: TrustView
    pacing: PacingView
    # UI.md §5.1: issues are what needs attention, wins are the opportunities beside it.
    attention: list[OpportunitySummary]
    wins: list[OpportunitySummary]
    # What is under test, which is the last section of the screen.
    experiments: ExperimentsToday
    # An analysis is in flight, so the numbers shown are the previous run's.
    analysing: bool


class TodayService:
    def __init__(self, session: Session) -> None:
        self._facts = FactRepository(session)
        self._settings = SettingsRepository(session)
        self._analysis = AnalysisRepository(session)
        self._metrics = MetricsService(session)
        self._trust = TrustService(session)
        self._pacing = PacingService(session)
        self._opportunities = OpportunityService(session)
        self._experiments = ExperimentService(session)

    def today(self) -> TodayView:
        settings = self._settings.get()
        trust = self._trust.check(self._facts.coverage())
        as_of = trust.as_of_date
        budgets = settings.monthly_budgets if settings else {}
        pacing = self._pacing.month(as_of, budgets or {})
        attention = self._opportunities.top("issue")
        wins = self._opportunities.top("win")
        experiments = self._experiments.today()
        analysing = self._analysis.is_running()
        if as_of is None:
            return TodayView(
                None,
                settings is not None,
                None,
                [],
                [],
                trust,
                pacing,
                attention,
                wins,
                experiments,
                analysing,
            )
        kpis = self._metrics.today(as_of, settings, unreliable_metrics(trust.sources))
        return TodayView(
            as_of,
            settings is not None,
            kpis.period,
            kpis.kpis,
            kpis.trend,
            trust,
            pacing,
            attention,
            wins,
            experiments,
            analysing,
        )
