"""Experiments: draft one from a recommendation, approve or reject it, list them (FR-10)."""

from __future__ import annotations

from fastapi import APIRouter

from mdia.api.deps import ExperimentServiceDep  # noqa: TC001 - FastAPI resolves it at runtime
from mdia.schemas.experiments import DecideIn, DraftIn, ExperimentListOut, ExperimentOut

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("", response_model=ExperimentListOut)
def list_experiments(service: ExperimentServiceDep) -> ExperimentListOut:
    """Every experiment, newest first: awaiting approval, running, and completed."""
    return ExperimentListOut.model_validate({"experiments": service.find()})


@router.post("", response_model=ExperimentOut)
def draft_experiment(body: DraftIn, service: ExperimentServiceDep) -> ExperimentOut:
    """Auto-fill an experiment from an opportunity's recommended action (FR-10.1)."""
    return ExperimentOut.model_validate(service.draft(body.opportunity_id))


@router.get("/{experiment_id}", response_model=ExperimentOut)
def get_experiment(experiment_id: int, service: ExperimentServiceDep) -> ExperimentOut:
    return ExperimentOut.model_validate(service.get(experiment_id))


@router.post("/{experiment_id}/approve", response_model=ExperimentOut)
def approve_experiment(
    experiment_id: int, body: DecideIn, service: ExperimentServiceDep
) -> ExperimentOut:
    """Accept the change: the test starts running against the next days of data (FR-10.2)."""
    return ExperimentOut.model_validate(service.approve(experiment_id, body.reason))


@router.post("/{experiment_id}/reject", response_model=ExperimentOut)
def reject_experiment(
    experiment_id: int, body: DecideIn, service: ExperimentServiceDep
) -> ExperimentOut:
    """Turn the change down; the opportunity stays open."""
    return ExperimentOut.model_validate(service.reject(experiment_id, body.reason))
