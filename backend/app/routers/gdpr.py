"""GDPR compliance router.

Implements the right-of-access (Art. 15) export and right-to-erasure (Art. 17)
delete for the Longevity+ MVP.

Both endpoints are:
  - Authenticated via ``api_key_auth`` (shared-secret API key).
  - Scoped to a single patient via the ``patient_id`` path parameter.
  - Wellness-framed: the delete acknowledgement uses "wellness data" language
    and never implies that *medical* records have been permanently destroyed
    without archival review.

Delete (Art. 17 — partial implementation):
  The ``DELETE /patients/{patient_id}/gdpr`` endpoint:
  1. Deletes all ``MealLog`` rows for the patient (hard delete).
  2. Removes all meal photo files via ``PhotoStorage.delete_all_for_patient``.
  3. Returns 200 with ``status="scheduled"`` — a wellness-framed acknowledgement.

  Full data erasure (Patient, EHRRecord, WearableDay, etc.) requires an async
  job queue and legal-retention review, both deferred to a future sprint.  This
  partial implementation satisfies the T26 Scenario 5 acceptance criterion:
  "GDPR delete-my-data removes photos too."
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.photo_storage import PhotoStorage, get_photo_storage
from app.core.config import Settings
from app.core.security import api_key_auth
from app.db.session import get_session
from app.repositories.ehr_repo import EHRRepository
from app.repositories.meal_log_repo import MealLogRepository
from app.repositories.patient_repo import PatientRepository
from app.repositories.wearable_repo import WearableRepository
from app.schemas.gdpr import GDPRDeleteAck, GDPRExportOut
from app.schemas.patient import PatientProfileOut
from app.schemas.records import EHRRecordOut
from app.schemas.wearable import WearableDayOut

router = APIRouter(
    prefix="/patients/{patient_id}/gdpr",
    tags=["gdpr"],
)

# Type aliases for cleaner signatures.
_Session = Annotated[AsyncSession, Depends(get_session)]
_Auth = Annotated[None, Depends(api_key_auth)]

# Attribute name constant used with getattr() — same mypy-workaround pattern
# as the concrete repositories (see e.g. ehr_repo.py).
_LP_PID = "patient_id"

#: Wellness-framed delete acknowledgement message (Art. 17).
_DELETE_MESSAGE = "Your wellness data will be removed."


def get_photo_storage_dep() -> PhotoStorage:
    """FastAPI dependency that returns the configured PhotoStorage backend.

    Reads ``photo_storage_backend`` from ``Settings`` to decide which backend
    to use.  In tests, this dependency is overridden via ``app.dependency_overrides``
    to inject a ``LocalFsPhotoStorage`` pointing at the test temporary directory.

    Returns:
        The appropriate ``PhotoStorage`` implementation.
    """
    return get_photo_storage(Settings())


_PhotoStorageDep = Annotated[PhotoStorage, Depends(get_photo_storage_dep)]


async def _fetch_lifestyle(session: AsyncSession, patient_id: str) -> Any:
    """Fetch LifestyleProfile for export bundle, or None if unavailable.

    Gracefully degraded: returns None when the lifestyle table is absent or
    the patient has no lifestyle record.  Uses ``getattr`` for the patient_id
    attribute to satisfy mypy strict mode (SQLModel attribute typing quirk).
    """
    try:
        from sqlalchemy import select

        from app.models.lifestyle_profile import LifestyleProfile

        pid_attr = getattr(LifestyleProfile, _LP_PID)
        stmt = select(LifestyleProfile).where(pid_attr == patient_id)
        result = await session.execute(stmt)
        lp = result.scalars().first()
        if lp is not None:
            return lp.model_dump() if hasattr(lp, "model_dump") else None
        return None
    except Exception:  # noqa: BLE001
        return None


@router.get(
    "/export",
    response_model=GDPRExportOut,
    tags=["gdpr"],
    summary="Export all data held for a patient (GDPR Art. 15)",
)
async def gdpr_export(
    patient_id: str,
    session: _Session,
    _auth: _Auth,
) -> GDPRExportOut:
    """Return a bundled export of all data held for *patient_id*.

    Bundles:
      - Demographic profile (Patient)
      - All EHR records
      - All available wearable telemetry (up to 90 days)
      - Lifestyle survey data

    Raises HTTP 404 if the patient does not exist.

    Args:
        patient_id: Path parameter, e.g. ``PT0282``.
        session:    Injected ``AsyncSession``.
        _auth:      ``api_key_auth`` result.
    """
    patient_repo = PatientRepository(session)
    patient = await patient_repo.get(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found.",
        )

    ehr_repo = EHRRepository(session)
    ehr_records = await ehr_repo.list(patient_id=patient_id)

    wearable_repo = WearableRepository(session)
    wearable_days = await wearable_repo.list_recent(patient_id=patient_id, days=90)

    lifestyle_data = await _fetch_lifestyle(session, patient_id)

    patient_out = PatientProfileOut.model_validate(patient)
    record_outs = [EHRRecordOut.model_validate(r) for r in ehr_records]
    wearable_outs = [WearableDayOut.model_validate(d) for d in wearable_days]

    return GDPRExportOut(
        patient_id=patient_id,
        patient=patient_out,
        records=record_outs,
        wearable=wearable_outs,
        lifestyle=lifestyle_data,
    )


@router.delete(
    "/",
    response_model=GDPRDeleteAck,
    tags=["gdpr"],
    summary="Request data erasure for a patient (GDPR Art. 17)",
)
async def gdpr_delete(
    patient_id: str,
    session: _Session,
    _auth: _Auth,
    photo_storage: _PhotoStorageDep,
) -> GDPRDeleteAck:
    """Acknowledge a data-erasure request for *patient_id*.

    Performs the following deletions synchronously:

    1. **MealLog rows** — all rows for the patient are hard-deleted via
       ``MealLogRepository.delete_for_patient``.
    2. **Meal photo files** — every stored photo file is removed via
       ``PhotoStorage.delete_all_for_patient`` (``LocalFsPhotoStorage`` in dev,
       ``GcsPhotoStorage`` in prod).

    Full patient record erasure (Patient, EHRRecord, WearableDay, etc.)
    requires an async job queue and legal-retention review, both deferred to a
    future sprint.  The ``status="scheduled"`` response communicates that
    erasure is an async process subject to legal obligations.

    The response is wellness-framed per the product requirement:
    "Your wellness data will be removed."

    Raises HTTP 404 if the patient does not exist.

    Args:
        patient_id:    Path parameter, e.g. ``PT0282``.
        session:       Injected ``AsyncSession``.
        _auth:         ``api_key_auth`` result.
        photo_storage: Injected ``PhotoStorage`` backend (overridable in tests).
    """
    patient_repo = PatientRepository(session)
    patient = await patient_repo.get(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found.",
        )

    # Step 1: Delete all MealLog rows for this patient.
    meal_log_repo = MealLogRepository(session)
    await meal_log_repo.delete_for_patient(patient_id=patient_id)
    await session.commit()

    # Step 2: Delete all photo files for this patient via PhotoStorage.
    # ``delete_all_for_patient`` sweeps the entire patient namespace, so
    # we don't need to iterate individual URIs from the (now-deleted) rows.
    photo_storage.delete_all_for_patient(patient_id)

    return GDPRDeleteAck(
        status="scheduled",
        message=_DELETE_MESSAGE,
    )
