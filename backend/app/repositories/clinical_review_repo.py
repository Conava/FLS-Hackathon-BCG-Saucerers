"""ClinicalReviewRepository — patient-scoped access to ClinicalReview rows.

Stack: SQLAlchemy 2.0 async (select() + session.execute()), SQLModel table models.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinical_review import ClinicalReview
from app.repositories.base import PatientScopedRepository

# SQLModel generates mapped attributes whose __eq__ returns a Python bool at
# the Python level, but a ColumnElement at runtime.  mypy strict mode rejects
# Model.col == value in .where() because it infers bool.  We retrieve the
# attribute via getattr() (typed Any) so mypy accepts the expression while
# the generated SQL is identical.  This pattern mirrors the base repository.
_PID = "patient_id"
_CREATED_AT = "created_at"
_ID = "id"


class ClinicalReviewRepository(PatientScopedRepository[ClinicalReview]):
    """Async repository for ClinicalReview — enforces patient_id isolation.

    Every query filters ``WHERE patient_id = :pid`` at the SQL level.
    Cross-patient reads are structurally impossible.

    Usage::

        repo = ClinicalReviewRepository(session)
        review = await repo.create(patient_id="PT0001", review=cr)
        reviews = await repo.list(patient_id="PT0001")
        fetched = await repo.get(patient_id="PT0001", record_id=review.id)
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=ClinicalReview)

    async def create(
        self, *, patient_id: str, review: ClinicalReview
    ) -> ClinicalReview:
        """Persist a new ClinicalReview row, defensively setting patient_id.

        Args:
            patient_id: The patient this review belongs to.
            review:     The ClinicalReview instance to persist.

        Returns:
            The persisted ClinicalReview instance with id populated.
        """
        # Defensive set — overwrites whatever the caller placed on the object.
        object.__setattr__(review, "patient_id", patient_id)
        self._session.add(review)
        await self._session.flush()
        return review

    async def get(  # type: ignore[override]
        self,
        *,
        patient_id: str,
        record_id: int,
    ) -> ClinicalReview | None:
        """Fetch a single ClinicalReview by patient_id + id.

        Returns ``None`` if the record does not exist or belongs to a
        different patient.

        Args:
            patient_id: The patient whose records are in scope.
            record_id:  The surrogate id of the ClinicalReview.

        Returns:
            The matching ClinicalReview, or ``None``.
        """
        pid_attr = getattr(ClinicalReview, _PID)
        id_attr = getattr(ClinicalReview, _ID)

        stmt = (
            select(ClinicalReview)
            .where(pid_attr == patient_id)
            .where(id_attr == record_id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def list(  # type: ignore[override]
        self,
        *,
        patient_id: str,
    ) -> list[ClinicalReview]:
        """List all ClinicalReview rows for a patient, ordered by created_at DESC.

        Args:
            patient_id: The patient whose reviews are in scope.

        Returns:
            A list of ClinicalReview instances, newest first.
        """
        pid_attr = getattr(ClinicalReview, _PID)
        created_at_attr = getattr(ClinicalReview, _CREATED_AT)

        stmt = (
            select(ClinicalReview)
            .where(pid_attr == patient_id)
            .order_by(created_at_attr.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
