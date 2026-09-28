"""Data trust per source (FR-5)."""

from __future__ import annotations

from fastapi import APIRouter

from mdia.api.deps import TrustServiceDep  # noqa: TC001 - FastAPI resolves it at runtime
from mdia.schemas.trust import TrustOut

router = APIRouter(prefix="/trust", tags=["trust"])


@router.get("", response_model=TrustOut)
def trust(service: TrustServiceDep) -> TrustOut:
    """Freshness of every source and, for ad channels, a tracking check against store orders."""
    return TrustOut.model_validate(service.check())
