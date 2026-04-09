"""ClinicalReviewService — stub persistence for clinician review requests.

This is a pure persistence stub.  No workflow logic (task assignment,
notification dispatch, status transitions) is implemented in the MVP.  A
``ClinicalReview`` row is created with ``status="pending"`` and returned.

The ``ai_flag`` payload (structured AI-generated risk context) is an internal
field that is **not** shown to patients.  Callers must ensure all patient-
facing text uses wellness framing only.

Usage::

    from app.services.clinical_review import ClinicalReviewService

    service = ClinicalReviewService(session=session)
    review = await service.create(
        patient_id="PT0001",
        reason="Elevated cardiovascular markers detected in wellness check",
        ai_flag={"signal": "elevated_apob", "severity": "moderate"},
    )
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinical_review import ClinicalReview
from app.repositories.clinical_review_repo import ClinicalReviewRepository


class ClinicalReviewService:
    """Persist clinician review requests with hard patient_id scoping.

    Args:
        session: An open ``AsyncSession`` (injected by FastAPI / test fixture).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ClinicalReviewRepository(session)

    async def create(
        self,
        *,
        patient_id: str,
        reason: str,
        ai_flag: dict[str, Any] | None,
    ) -> ClinicalReview:
        """Create a new clinician review request for a patient.

        Creates a ``ClinicalReview`` row with ``status="pending"``.
        Patient isolation is enforced at the repository layer — the repo
        overwrites any ``patient_id`` on the model with the value supplied
        here, making cross-patient writes structurally impossible.

        Args:
            patient_id: The patient this review request belongs to.
            reason:     Human-readable wellness-framed reason for the review.
                        Must not contain diagnostic verbs (diagnose/treat/cure).
            ai_flag:    Optional structured AI risk context for internal use
                        only — never shown to the patient directly.

        Returns:
            The persisted ``ClinicalReview`` instance with ``id`` populated.
        """
        review = ClinicalReview(
            patient_id=patient_id,
            reason=reason,
            ai_flag=ai_flag,
            status="pending",
        )
        return await self._repo.create(patient_id=patient_id, review=review)
