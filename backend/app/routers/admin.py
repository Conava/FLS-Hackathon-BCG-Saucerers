"""Admin router — seed and reseed endpoints for demo data management.

Provides two endpoints for loading CSV data into the database:

* ``POST /v1/admin/seed``   — idempotent load; skips/upserts existing patients.
* ``POST /v1/admin/reseed`` — nuke-and-reload: deletes all rows from every table
                              then re-runs the full seed.

Both endpoints:
  - Require ``X-API-Key`` authentication via ``api_key_auth``.
  - Use ``CSVDataSource`` (registered as ``"csv"``) under the hood, delegating
    to ``UnifiedProfileService.ingest()``.
  - Return a JSON summary of counts.

Data files are read from ``/app/data/`` inside the container (docker-compose
volume mount: ``./data:/app/data:ro``).

PHI policy: no patient names, IDs, or record contents are logged. Only
aggregate counts and duration are emitted.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

import app.adapters.csv_source  # noqa: F401 — side-effect: @register("csv") fires
from app.core.logging import get_logger
from app.core.security import api_key_auth
from app.db.session import get_session
from app.models import (
    ClinicalReview,
    DailyLog,
    EHRRecord,
    LifestyleProfile,
    MealLog,
    Message,
    Notification,
    Patient,
    Protocol,
    ProtocolAction,
    Referral,
    SurveyResponse,
    VitalityOutlook,
    VitalitySnapshot,
    WearableDay,
)
from app.services.unified_profile import UnifiedProfileService

router = APIRouter(prefix="/admin", tags=["admin"])

# Type aliases for cleaner signatures — same pattern as all other routers.
_Session = Annotated[AsyncSession, Depends(get_session)]
_Auth = Annotated[None, Depends(api_key_auth)]

#: Data directory inside the container (matches docker-compose volume mount).
_DATA_DIR = Path("/app/data")

_logger: logging.Logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Delete ordering — child tables before parent to satisfy FK constraints.
# Reverse of creation order; Patient is always last.
# ---------------------------------------------------------------------------

#: Ordered list of SQLModel classes to delete in reseed, safest order first.
_DELETE_ORDER: list[Any] = [
    # Protocol children first
    ProtocolAction,
    Protocol,
    # Survey children
    SurveyResponse,
    # Other patient-child tables (no FK to each other, order arbitrary)
    VitalityOutlook,
    VitalitySnapshot,
    ClinicalReview,
    Referral,
    Notification,
    Message,
    DailyLog,
    MealLog,
    EHRRecord,
    WearableDay,
    LifestyleProfile,
    # Patient last — all FKs point to it
    Patient,
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _run_seed(session: AsyncSession) -> dict[str, Any]:
    """Run the full CSV ingest and return a summary dict.

    Uses ``UnifiedProfileService.ingest`` which is idempotent per-patient via
    ``session.merge()`` for Patient/LifestyleProfile and delete-then-insert for
    EHRRecord/WearableDay/DailyLog/MealLog rows.

    Args:
        session: An open ``AsyncSession`` to write into.

    Returns:
        A dict with keys ``patients_seeded``, ``ehr_records``,
        ``wearable_days``, and ``duration_seconds``.
    """
    if not _DATA_DIR.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Data directory not found: {_DATA_DIR}. Is the volume mounted?",
        )

    svc = UnifiedProfileService(session)
    try:
        report = await svc.ingest("csv", data_dir=_DATA_DIR)
    except Exception as exc:
        _logger.error("seed_failed", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Seed failed: {exc}",
        ) from exc

    return {
        "patients_seeded": report.patients_ingested,
        "ehr_records": report.ehr_records,
        "wearable_days": report.wearable_days,
        "duration_seconds": round(report.duration_seconds, 2),
    }


async def _delete_all(session: AsyncSession) -> None:
    """Delete all rows from every table in FK-safe order.

    Iterates ``_DELETE_ORDER`` issuing a DELETE (no WHERE clause) for each
    SQLModel class.  All deletes run in the same transaction as the subsequent
    seed, so a seed failure rolls back the deletes atomically.

    Args:
        session: An open ``AsyncSession`` to write into.
    """
    for model_cls in _DELETE_ORDER:
        await session.execute(delete(model_cls))
    # Flush deletes before the seed inserts begin.
    await session.flush()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/seed",
    summary="Load CSV data into the database (idempotent)",
    response_description="Summary of records loaded",
)
async def seed(
    session: _Session,
    _auth: _Auth,
) -> dict[str, Any]:
    """Load all CSV patient data into the database.

    Idempotent: existing rows are upserted via ``session.merge()`` (Patient,
    LifestyleProfile) or cleared per-patient before re-insertion (EHRRecord,
    WearableDay, DailyLog, MealLog).  Running this endpoint multiple times on
    the same CSV files leaves the database in the same state.

    Returns:
        JSON object with ``patients_seeded``, ``ehr_records``,
        ``wearable_days``, and ``duration_seconds``.

    Raises:
        503: Data directory not found (volume not mounted).
        500: Unexpected ingest error.
    """
    _logger.info("admin_seed_started")
    summary = await _run_seed(session)
    _logger.info("admin_seed_complete", extra=summary)
    return summary


@router.post(
    "/reseed",
    summary="Delete all data then reload from CSV (demo reset)",
    response_description="Summary of records loaded after reset",
)
async def reseed(
    session: _Session,
    _auth: _Auth,
) -> dict[str, Any]:
    """Nuke-and-reload: delete ALL rows from every table, then seed from CSV.

    Designed for demo resets. Deletes in FK-safe order (children before
    parents), then runs the full CSV ingest.  The delete and seed share one
    transaction — a seed failure rolls back the deletes.

    Returns:
        JSON object with ``patients_seeded``, ``ehr_records``,
        ``wearable_days``, and ``duration_seconds``.

    Raises:
        503: Data directory not found (volume not mounted).
        500: Unexpected error during delete or ingest.
    """
    _logger.info("admin_reseed_started")
    try:
        await _delete_all(session)
    except Exception as exc:
        _logger.error("reseed_delete_failed", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reseed delete phase failed: {exc}",
        ) from exc

    summary = await _run_seed(session)
    _logger.info("admin_reseed_complete", extra=summary)
    return summary
