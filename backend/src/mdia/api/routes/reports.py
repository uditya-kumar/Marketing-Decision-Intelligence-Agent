"""The weekly report: generate one, list the history, read one back (FR-11)."""

from __future__ import annotations

from fastapi import APIRouter, status

from mdia.api.deps import ReportServiceDep  # noqa: TC001 - FastAPI resolves it at runtime
from mdia.schemas.reports import GenerateReportIn, ReportListOut, ReportOut

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/weekly", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def generate(body: GenerateReportIn, service: ReportServiceDep) -> ReportOut:
    """Build the week's facts and narrate them, replacing any earlier report for it."""
    return ReportOut.model_validate(service.generate(body.week_end))


@router.get("", response_model=ReportListOut)
def list_reports(service: ReportServiceDep) -> ReportListOut:
    """Past reports, newest first, with the week a fresh one would cover."""
    return ReportListOut.model_validate(service.find())


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: int, service: ReportServiceDep) -> ReportOut:
    return ReportOut.model_validate(service.get(report_id))
