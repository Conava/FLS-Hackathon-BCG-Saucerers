"""WearableRepository — patient-scoped access to WearableDay rows.

Inherits from ``PatientScopedRepository[WearableDay]`` and adds the
``list_recent`` query that returns the N most recent wearable days for a
patient, ordered by ``date DESC``.

Stack: SQLAlchemy 2.0 async, sqlalchemy.select() + session.execute().
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wearable_day import WearableDay
from app.repositories.base import PatientScopedRepository

# SQLModel generates mapped attributes whose __eq__ returns a Python bool at
# the Python level, but a ColumnElement at runtime.  mypy strict mode rejects
# Model.col == value in .where() because it infers bool.  We retrieve the
# attribute via getattr() (typed Any) so mypy accepts the expression while
# the generated SQL is identical.  This pattern mirrors the base repository.
_PID = "patient_id"
_DATE = "date"


class WearableRepository(PatientScopedRepository[WearableDay]):
    """Async repository for WearableDay — enforces patient_id isolation.

    Every query filters ``WHERE patient_id = :pid`` at the SQL level.

    Usage::

        repo = WearableRepository(session)
        days = await repo.list_recent(patient_id="PT0001", days=7)
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=WearableDay)

    async def list_recent(
        self,
        *,
        patient_id: str,
        days: int = 7,
    ) -> list[WearableDay]:
        """Return the N most recent wearable-day rows for a patient.

        Rows are ordered by ``date DESC`` so index 0 is the most recent day.
        The LIMIT is applied in SQL — no post-filter in Python.

        Args:
            patient_id: The patient whose telemetry is in scope (required).
            days:       Maximum number of rows to return (default 7).

        Returns:
            Up to ``days`` ``WearableDay`` instances, newest first.
        """
        pid_attr = getattr(WearableDay, _PID)
        date_attr = getattr(WearableDay, _DATE)

        stmt = (
            select(WearableDay)
            .where(pid_attr == patient_id)
            .order_by(date_attr.desc())
            .limit(days)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
