"""Referral router.

Provides a single endpoint that creates a specialist referral for a patient.

Endpoint:
    POST /patients/{patient_id}/referral

Authentication:
    Every request must carry a valid ``X-API-Key`` header (enforced by
    ``api_key_auth``).

Isolation guarantee:
    The ``patient_id`` path parameter flows directly into
    ``ReferralService.create`` which hard-scopes writes to the given patient.
    Cross-patient writes are structurally impossible at the repository layer.

Schema mapping note:
    The inbound ``ReferralIn`` carries ``specialty`` and ``reason`` fields.
    The ``Referral`` model only stores a ``code`` (and the standard metadata).
    This router generates a unique referral code that encodes the specialty
    prefix (e.g. ``"REF-CARDIO-<uuid_hex[:8].upper()>"``) and returns a
    response that surfaces ``specialty`` and ``reason`` from the original
    request alongside the persisted ``code`` and ``status``.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import api_key_auth
from app.db.session import get_session
from app.repositories.patient_repo import PatientRepository
from app.schemas.referral import ReferralIn
from app.services.referral import ReferralService

router = APIRouter(prefix="/patients", tags=["referral"])

# Type alias for the session dependency to keep signatures concise.
_Session = Annotated[AsyncSession, Depends(get_session)]
_Auth = Annotated[None, Depends(api_key_auth)]


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------


class ReferralResponse(BaseModel):
    """API response for a persisted Referral row.

    Surfaces the original ``specialty`` and ``reason`` from the request
    alongside the generated ``code`` and the standard ``status`` /
    ``created_at`` fields.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Referral primary key")
    patient_id: str = Field(..., description="Patient the referral belongs to")
    code: str = Field(..., description="Unique shareable referral code")
    specialty: str = Field(..., description="Target medical specialty")
    reason: str = Field(..., description="Wellness-framed referral reason")
    status: str = Field(
        ...,
        description="Referral status: 'pending' | 'sent' | 'completed'",
    )
    created_at: datetime.datetime = Field(
        ...,
        description="Timestamp when the referral was created (naive UTC)",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_code(specialty: str) -> str:
    """Generate a unique referral code prefixed with the specialty slug.

    Format: ``REF-{SPECIALTY_SLUG}-{UUID_HEX[:8].upper()}``
    Example: ``REF-CARDIO-3F2A1B4C``

    Args:
        specialty: The medical specialty string, e.g. ``"cardiology"``.

    Returns:
        A unique referral code string.
    """
    slug = specialty.upper()[:6]  # e.g. "CARDIO" from "cardiology"
    uid = uuid.uuid4().hex[:8].upper()
    return f"REF-{slug}-{uid}"


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/{patient_id}/referral",
    response_model=ReferralResponse,
    tags=["referral"],
    summary="Create a specialist referral for a patient",
)
async def post_referral(
    patient_id: str,
    body: ReferralIn,
    session: _Session,
    _auth: _Auth,
) -> ReferralResponse:
    """Create a referral record and persist it.

    The endpoint:
    1. Validates that the patient exists — returns 404 if not.
    2. Generates a unique referral code from the specialty.
    3. Delegates to ``ReferralService.create`` which persists a ``Referral``
       row with ``status="pending"``.
    4. Returns a response that includes ``specialty`` and ``reason`` from the
       original request alongside the stored ``code`` and ``status``.

    Isolation guarantee:
        The ``patient_id`` path parameter is the sole scope key.  The service
        enforces ``patient_id`` scoping at the repository layer.

    Args:
        patient_id: Path parameter — the referring patient, e.g. ``PT0282``.
        body:       Request body with ``specialty`` and ``reason``.
        session:    Injected ``AsyncSession`` (per-request).
        _auth:      ``api_key_auth`` result (validates ``X-API-Key`` header).

    Returns:
        ``ReferralResponse`` with id, patient_id, code, specialty, reason,
        status, and created_at.

    Raises:
        HTTPException 404: If ``patient_id`` does not exist in the database.
    """
    # Guard: patient must exist before creating a referral.
    patient_repo = PatientRepository(session)
    patient = await patient_repo.get(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found.",
        )

    code = _generate_code(body.specialty)
    service = ReferralService(session=session)
    referral = await service.create(patient_id=patient_id, code=code)

    return ReferralResponse(
        id=referral.id,
        patient_id=referral.patient_id,
        code=referral.code,
        specialty=body.specialty,
        reason=body.reason,
        status=referral.status,
        created_at=referral.created_at,
    )
