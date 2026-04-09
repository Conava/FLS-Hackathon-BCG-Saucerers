"""MealLogRepository — patient-scoped access to MealLog rows.

Includes ``delete_for_patient`` for GDPR Art. 17 (right to erasure) compliance.
The caller (GDPR service) is responsible for also deleting the associated photo
files via the PhotoStorage adapter before or after calling this method.

Stack: SQLAlchemy 2.0 async (select() + session.execute()), SQLModel table models.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meal_log import MealLog
from app.repositories.base import PatientScopedRepository

# SQLModel generates mapped attributes whose __eq__ returns a Python bool at
# the Python level, but a ColumnElement at runtime.  mypy strict mode rejects
# Model.col == value in .where() because it infers bool.  We retrieve the
# attribute via getattr() (typed Any) so mypy accepts the expression while
# the generated SQL is identical.  This pattern mirrors the base repository.
_PID = "patient_id"
_ANALYZED_AT = "analyzed_at"
_ID = "id"


class MealLogRepository(PatientScopedRepository[MealLog]):
    """Async repository for MealLog — enforces patient_id isolation.

    Every query filters ``WHERE patient_id = :pid`` at the SQL level.
    Cross-patient reads are structurally impossible.

    ``delete_for_patient`` supports GDPR Art. 17 right-to-erasure: removes all
    meal log rows for a patient.  Photo file deletion is handled separately by
    the GDPR service via the PhotoStorage adapter.

    Usage::

        repo = MealLogRepository(session)
        meal = await repo.create(patient_id="PT0001", meal=m)
        history = await repo.list_recent(patient_id="PT0001", limit=10)
        await repo.delete_for_patient(patient_id="PT0001")
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=MealLog)

    async def create(self, *, patient_id: str, meal: MealLog) -> MealLog:
        """Persist a new MealLog row, defensively setting patient_id.

        Args:
            patient_id: The patient this meal log belongs to.
            meal:       The MealLog instance to persist.

        Returns:
            The persisted MealLog instance with id populated.
        """
        # Defensive set — overwrites whatever the caller placed on the object.
        object.__setattr__(meal, "patient_id", patient_id)
        self._session.add(meal)
        await self._session.flush()
        return meal

    async def get(  # type: ignore[override]
        self,
        *,
        patient_id: str,
        record_id: int,
    ) -> MealLog | None:
        """Fetch a single MealLog by patient_id + id.

        Returns ``None`` if the record does not exist or belongs to a
        different patient.

        Args:
            patient_id: The patient whose records are in scope.
            record_id:  The surrogate id of the MealLog.

        Returns:
            The matching MealLog, or ``None``.
        """
        pid_attr = getattr(MealLog, _PID)
        id_attr = getattr(MealLog, _ID)

        stmt = (
            select(MealLog)
            .where(pid_attr == patient_id)
            .where(id_attr == record_id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def list_recent(
        self,
        *,
        patient_id: str,
        limit: int = 20,
    ) -> list[MealLog]:
        """Return the most recent MealLog rows for a patient.

        Rows are ordered by ``analyzed_at DESC`` so index 0 is the most
        recent meal.  The LIMIT is applied in SQL — no post-filter in Python.

        Args:
            patient_id: The patient whose logs are in scope (required).
            limit:      Maximum number of rows to return (default 20).

        Returns:
            Up to ``limit`` MealLog instances, newest first.
        """
        pid_attr = getattr(MealLog, _PID)
        analyzed_at_attr = getattr(MealLog, _ANALYZED_AT)

        stmt = (
            select(MealLog)
            .where(pid_attr == patient_id)
            .order_by(analyzed_at_attr.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_for_patient(self, *, patient_id: str) -> None:
        """Delete all MealLog rows for a patient (GDPR Art. 17 right to erasure).

        This is a hard delete — rows are permanently removed.  The caller is
        responsible for also deleting associated photo files via the
        PhotoStorage adapter.

        Args:
            patient_id: The patient whose meal logs are to be deleted.
        """
        pid_attr = getattr(MealLog, _PID)
        stmt = delete(MealLog).where(pid_attr == patient_id)
        await self._session.execute(stmt)
        await self._session.flush()
