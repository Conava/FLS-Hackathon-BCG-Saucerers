"""ReferralService — stub persistence for patient referral records.

This is a pure persistence stub.  No referral-code validation, expiry
logic, or redemption workflow is implemented in the MVP.  A ``Referral``
row is created with ``status="pending"`` and returned.

The referral code is provided by the caller (e.g. the router generates it
with ``uuid4``).  The ``referred_patient_id`` is ``None`` until the referred
person signs up and is linked externally.

Usage::

    from app.services.referral import ReferralService

    service = ReferralService(session=session)
    referral = await service.create(
        patient_id="PT0001",
        code="REF-ABCD-1234",
    )
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.referral import Referral
from app.repositories.referral_repo import ReferralRepository


class ReferralService:
    """Persist referral records with hard patient_id scoping.

    Args:
        session: An open ``AsyncSession`` (injected by FastAPI / test fixture).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ReferralRepository(session)

    async def create(
        self,
        *,
        patient_id: str,
        code: str,
    ) -> Referral:
        """Create a new referral record for a patient.

        Creates a ``Referral`` row with ``status="pending"`` and
        ``referred_patient_id=None``.  Patient isolation is enforced at
        the repository layer — the repo overwrites any ``patient_id`` on
        the model with the value supplied here, making cross-patient
        writes structurally impossible.

        Args:
            patient_id: The referring patient.
            code:       The unique shareable referral code
                        (e.g. ``"REF-ABCD-1234"``).

        Returns:
            The persisted ``Referral`` instance with ``id`` populated.
        """
        referral = Referral(
            patient_id=patient_id,
            code=code,
            status="pending",
        )
        return await self._repo.create(patient_id=patient_id, referral=referral)
