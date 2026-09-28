"""Ingestion routes: CSV upload, run history, source status and templates (FR-3)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Query, UploadFile

from mdia.api.deps import IngestionServiceDep  # noqa: TC001 - FastAPI resolves it at runtime
from mdia.schemas.ingestion import (
    IngestionRunOut,
    IngestionStatusOut,
    TemplateOut,
    UploadResponse,
)
from mdia.services.analysis import run_analysis
from mdia.services.ingestion import UploadedFile

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/upload", response_model=UploadResponse)
def upload(
    files: Annotated[list[UploadFile], File(description="One or more platform CSV exports")],
    service: IngestionServiceDep,
    background: BackgroundTasks,
) -> UploadResponse:
    """Detect each file's source, load its valid rows and report the rejected ones.

    New data means the signals are stale, so the analysis re-runs in the background.
    """
    uploaded = [UploadedFile(f.filename or "upload.csv", f.file.read()) for f in files]
    response = UploadResponse.model_validate(service.upload(uploaded))
    if any(run.rows_accepted for run in response.runs):
        background.add_task(run_analysis)
    return response


@router.get("/runs", response_model=list[IngestionRunOut])
def runs(
    service: IngestionServiceDep, limit: Annotated[int, Query(ge=1, le=200)] = 50
) -> list[IngestionRunOut]:
    """Most recent ingestion runs first, each with a sample of its rejected rows."""
    return [IngestionRunOut.model_validate(run) for run in service.recent_runs(limit)]


@router.get("/status", response_model=IngestionStatusOut)
def status(service: IngestionServiceDep) -> IngestionStatusOut:
    """Per-source coverage, missing sources and the as-of date."""
    return IngestionStatusOut.model_validate(service.status())


@router.get("/templates", response_model=list[TemplateOut])
def templates(service: IngestionServiceDep) -> list[TemplateOut]:
    """Expected columns for every supported export, for the downloadable CSV templates."""
    return [TemplateOut.from_template(template) for template in service.templates()]
