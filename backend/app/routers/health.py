"""Health check router.

``GET /healthz`` — unauthenticated liveness probe for Cloud Run and
load-balancer health checks.  Returns a minimal JSON body; no PHI, no session,
no auth dependency.

This router is mounted at the app root (no prefix) so the path is literally
``/healthz``.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Liveness response body."""

    status: str


@router.get(
    "/healthz",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns {status: ok} with no authentication required.",
)
async def healthz() -> HealthResponse:
    """Return a simple liveness signal.

    No database access, no auth dependency — intentionally minimal so the
    Cloud Run health check never fails due to DB connectivity issues.
    """
    return HealthResponse(status="ok")
