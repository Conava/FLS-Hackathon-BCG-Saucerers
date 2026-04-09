"""GDPR compliance router.

Implements the right-of-access (Art. 15) export and right-to-erasure (Art. 17)
delete stub for the Longevity+ MVP.

Both endpoints are:
  - Authenticated via ``api_key_auth`` (shared-secret API key).
  - Scoped to a single patient via the ``patient_id`` path parameter.
  - Wellness-framed: the delete acknowledgement uses "wellness data" language
    and never implies that *medical* records have been permanently destroyed
    without archival review.

Delete is a STUB in this slice:
  The ``DELETE /patients/{patient_id}/gdpr`` endpoint returns a 200 with
  ``status="scheduled"`` and does not modify any data.  Actual deletion
  requires an async job queue and legal-retention review, both deferred to a
  future sprint.  This is documented here and in the OpenAPI description.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import api_key_auth
from app.db.session import get_session
from app.repositories.ehr_repo import EHRRepository
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
    summary="Request data erasure for a patient (GDPR Art. 17 — stub)",
)
async def gdpr_delete(
    patient_id: str,
    session: _Session,
    _auth: _Auth,
) -> GDPRDeleteAck:
    """Acknowledge a data-erasure request for *patient_id*.

    STUB — no data is deleted in this slice.  The response is wellness-framed
    per the product requirement: "Your wellness data will be removed."

    The ``status="scheduled"`` value communicates that erasure is an async
    process subject to legal retention obligations — it does not confirm that
    records have been permanently destroyed.

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

    return GDPRDeleteAck(
        status="scheduled",
        message=_DELETE_MESSAGE,
    )
