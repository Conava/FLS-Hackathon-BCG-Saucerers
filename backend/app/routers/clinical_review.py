"""Clinical review router.

Provides a single endpoint that creates a clinician review request for a patient.

Endpoint:
    POST /patients/{patient_id}/clinical-review

Authentication:
    Every request must carry a valid ``X-API-Key`` header (enforced by
    ``api_key_auth``).

Isolation guarantee:
    The ``patient_id`` path parameter flows directly into
    ``ClinicalReviewService.create`` which hard-scopes writes to the given
    patient.  Cross-patient writes are structurally impossible at the
    repository layer.

Schema mapping note:
    The inbound ``ClinicalReviewIn.notes`` field maps to the service's
    ``reason`` parameter and the ``ClinicalReview.reason`` model column.
    The response includes a ``notes`` alias for API backward compatibility.
    Both ``notes`` and ``reason`` are present in the response so clients
    that reference either field remain compatible.
"""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import api_key_auth
from app.db.session import get_session
from app.repositories.patient_repo import PatientRepository
from app.schemas.clinical_review import ClinicalReviewIn
from app.services.clinical_review import ClinicalReviewService

router = APIRouter(prefix="/patients", tags=["clinical-review"])

# Type alias for the session dependency to keep signatures concise.
_Session = Annotated[AsyncSession, Depends(get_session)]
_Auth = Annotated[None, Depends(api_key_auth)]


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------


class ClinicalReviewResponse(BaseModel):
    """API response for a persisted ClinicalReview row.

    Exposes both ``notes`` (the schema field name from the request) and
    ``reason`` (the model field name) so that callers can reference either.
    ``status`` is always ``"pending"`` on creation.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Clinical review primary key")
    patient_id: str = Field(..., description="Patient the review belongs to")
    notes: str = Field(..., description="Wellness concern notes (mirrors reason)")
    reason: str = Field(..., description="Reason stored on the review row")
    status: str = Field(
        ...,
        description="Review status: 'pending' | 'in_review' | 'resolved'",
    )
    created_at: datetime.datetime = Field(
        ...,
        description="Timestamp when the review was created (naive UTC)",
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/{patient_id}/clinical-review",
    response_model=ClinicalReviewResponse,
    tags=["clinical-review"],
    summary="Create a clinical review request for a patient",
)
async def post_clinical_review(
    patient_id: str,
    body: ClinicalReviewIn,
    session: _Session,
    _auth: _Auth,
) -> ClinicalReviewResponse:
    """Create a clinician review request and persist it.

    The endpoint:
    1. Validates that the patient exists — returns 404 if not.
    2. Maps ``ClinicalReviewIn.notes`` to the service's ``reason`` parameter.
    3. Delegates to ``ClinicalReviewService.create`` which persists a
       ``ClinicalReview`` row with ``status="pending"``.
    4. Returns a response that includes both ``notes`` and ``reason`` for
       API compatibility.

    Isolation guarantee:
        The ``patient_id`` path parameter is the sole scope key.  The service
        enforces ``patient_id`` scoping at the repository layer.

    Args:
        patient_id: Path parameter — the patient being flagged, e.g. ``PT0282``.
        body:       Request body with ``notes`` describing the wellness concern.
        session:    Injected ``AsyncSession`` (per-request).
        _auth:      ``api_key_auth`` result (validates ``X-API-Key`` header).

    Returns:
        ``ClinicalReviewResponse`` with id, patient_id, notes, reason, status,
        and created_at.

    Raises:
        HTTPException 404: If ``patient_id`` does not exist in the database.
    """
    # Guard: patient must exist before creating a review.
    patient_repo = PatientRepository(session)
    patient = await patient_repo.get(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found.",
        )

    service = ClinicalReviewService(session=session)
    # Map the schema's ``notes`` field to the service's ``reason`` parameter.
    review = await service.create(
        patient_id=patient_id,
        reason=body.notes,
        ai_flag=None,
    )

    return ClinicalReviewResponse(
        id=review.id,  # type: ignore[arg-type]
        patient_id=review.patient_id,
        notes=review.reason,
        reason=review.reason,
        status=review.status,
        created_at=review.created_at,
    )
