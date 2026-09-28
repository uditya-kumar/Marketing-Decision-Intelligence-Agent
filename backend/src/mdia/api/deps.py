"""FastAPI dependency providers: build services from a request-scoped session."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from mdia.db.session import get_session
from mdia.services.analysis import AnalysisService
from mdia.services.decisions import DecisionService
from mdia.services.experiments import ExperimentService
from mdia.services.ingestion import IngestionService
from mdia.services.metrics import MetricsService
from mdia.services.opportunities import OpportunityService
from mdia.services.reports import ReportService
from mdia.services.settings import SettingsService
from mdia.services.today import TodayService
from mdia.services.trust import TrustService

SessionDep = Annotated[Session, Depends(get_session)]


def get_analysis_service(session: SessionDep) -> AnalysisService:
    return AnalysisService(session)


AnalysisServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]


def get_ingestion_service(session: SessionDep) -> IngestionService:
    return IngestionService(session)


IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]


def get_settings_service(session: SessionDep) -> SettingsService:
    return SettingsService(session)


SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]


def get_metrics_service(session: SessionDep) -> MetricsService:
    return MetricsService(session)


MetricsServiceDep = Annotated[MetricsService, Depends(get_metrics_service)]


def get_trust_service(session: SessionDep) -> TrustService:
    return TrustService(session)


TrustServiceDep = Annotated[TrustService, Depends(get_trust_service)]


def get_opportunity_service(session: SessionDep) -> OpportunityService:
    return OpportunityService(session)


OpportunityServiceDep = Annotated[OpportunityService, Depends(get_opportunity_service)]


def get_experiment_service(session: SessionDep) -> ExperimentService:
    return ExperimentService(session)


ExperimentServiceDep = Annotated[ExperimentService, Depends(get_experiment_service)]


def get_decision_service(session: SessionDep) -> DecisionService:
    return DecisionService(session)


DecisionServiceDep = Annotated[DecisionService, Depends(get_decision_service)]


def get_today_service(session: SessionDep) -> TodayService:
    return TodayService(session)


TodayServiceDep = Annotated[TodayService, Depends(get_today_service)]


def get_report_service(session: SessionDep) -> ReportService:
    return ReportService(session)


ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]
