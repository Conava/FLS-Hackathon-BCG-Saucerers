"""ReferralRepository — patient-scoped access to Referral rows.

Stack: SQLAlchemy 2.0 async (select() + session.execute()), SQLModel table models.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.referral import Referral
from app.repositories.base import PatientScopedRepository

# SQLModel generates mapped attributes whose __eq__ returns a Python bool at
# the Python level, but a ColumnElement at runtime.  mypy strict mode rejects
# Model.col == value in .where() because it infers bool.  We retrieve the
# attribute via getattr() (typed Any) so mypy accepts the expression while
# the generated SQL is identical.  This pattern mirrors the base repository.
_PID = "patient_id"
_CODE = "code"
_ID = "id"


class ReferralRepository(PatientScopedRepository[Referral]):
    """Async repository for Referral — enforces patient_id isolation.

    Every query filters ``WHERE patient_id = :pid`` at the SQL level.
    Cross-patient reads are structurally impossible.

    ``get_by_code`` also enforces the patient_id scope — a code lookup without
    patient_id is not supported to prevent cross-patient code enumeration.

    Usage::

        repo = ReferralRepository(session)
        ref = await repo.create(patient_id="PT0001", referral=r)
        found = await repo.get_by_code(patient_id="PT0001", code="REF-ABCD-1234")
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Referral)

    async def create(self, *, patient_id: str, referral: Referral) -> Referral:
        """Persist a new Referral row, defensively setting patient_id.

        Args:
            patient_id: The patient this referral belongs to.
            referral:   The Referral instance to persist.

        Returns:
            The persisted Referral instance with id populated.
        """
        # Defensive set — overwrites whatever the caller placed on the object.
        object.__setattr__(referral, "patient_id", patient_id)
        self._session.add(referral)
        await self._session.flush()
        return referral

    async def get(  # type: ignore[override]
        self,
        *,
        patient_id: str,
        record_id: int,
    ) -> Referral | None:
        """Fetch a single Referral by patient_id + id.

        Returns ``None`` if the record does not exist or belongs to a
        different patient.

        Args:
            patient_id: The patient whose records are in scope.
            record_id:  The surrogate id of the Referral.

        Returns:
            The matching Referral, or ``None``.
        """
        pid_attr = getattr(Referral, _PID)
        id_attr = getattr(Referral, _ID)

        stmt = (
            select(Referral)
            .where(pid_attr == patient_id)
            .where(id_attr == record_id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def list(  # type: ignore[override]
        self,
        *,
        patient_id: str,
    ) -> list[Referral]:
        """List all Referral rows for a patient, ordered by id DESC.

        Args:
            patient_id: The patient whose referrals are in scope.

        Returns:
            A list of Referral instances, newest first.
        """
        pid_attr = getattr(Referral, _PID)
        id_attr = getattr(Referral, _ID)

        stmt = (
            select(Referral)
            .where(pid_attr == patient_id)
            .order_by(id_attr.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_code(self, *, patient_id: str, code: str) -> Referral | None:
        """Fetch a Referral by its shareable code, scoped to a patient.

        Cross-patient code enumeration is prevented because patient_id is
        always required alongside the code.

        Args:
            patient_id: The patient whose referrals are in scope.
            code:       The unique shareable referral code.

        Returns:
            The matching Referral, or ``None``.
        """
        pid_attr = getattr(Referral, _PID)
        code_attr = getattr(Referral, _CODE)

        stmt = (
            select(Referral)
            .where(pid_attr == patient_id)
            .where(code_attr == code)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()
