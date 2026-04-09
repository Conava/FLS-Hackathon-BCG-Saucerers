"""DailyLogRepository — patient-scoped access to DailyLog rows.

Stack: SQLAlchemy 2.0 async (select() + session.execute()), SQLModel table models.
"""

from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_log import DailyLog
from app.repositories.base import PatientScopedRepository

# SQLModel generates mapped attributes whose __eq__ returns a Python bool at
# the Python level, but a ColumnElement at runtime.  mypy strict mode rejects
# Model.col == value in .where() because it infers bool.  We retrieve the
# attribute via getattr() (typed Any) so mypy accepts the expression while
# the generated SQL is identical.  This pattern mirrors the base repository.
_PID = "patient_id"
_LOGGED_AT = "logged_at"
_ID = "id"


class DailyLogRepository(PatientScopedRepository[DailyLog]):
    """Async repository for DailyLog — enforces patient_id isolation.

    Every query filters ``WHERE patient_id = :pid`` at the SQL level.
    Cross-patient reads are structurally impossible.

    Usage::

        repo = DailyLogRepository(session)
        log = await repo.create(patient_id="PT0001", log=dl)
        logs = await repo.list_by_date_range(patient_id="PT0001", from_dt=..., to_dt=...)
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=DailyLog)

    async def create(self, *, patient_id: str, log: DailyLog) -> DailyLog:
        """Persist a new DailyLog row, defensively setting patient_id.

        Args:
            patient_id: The patient this log belongs to.
            log:        The DailyLog instance to persist.

        Returns:
            The persisted DailyLog instance with id populated.
        """
        # Defensive set — overwrites whatever the caller placed on the object.
        object.__setattr__(log, "patient_id", patient_id)
        self._session.add(log)
        await self._session.flush()
        return log

    async def get(  # type: ignore[override]
        self,
        *,
        patient_id: str,
        record_id: int,
    ) -> DailyLog | None:
        """Fetch a single DailyLog by patient_id + id.

        Returns ``None`` if the record does not exist or belongs to a
        different patient.

        Args:
            patient_id: The patient whose records are in scope.
            record_id:  The surrogate id of the DailyLog.

        Returns:
            The matching DailyLog, or ``None``.
        """
        pid_attr = getattr(DailyLog, _PID)
        id_attr = getattr(DailyLog, _ID)

        stmt = (
            select(DailyLog)
            .where(pid_attr == patient_id)
            .where(id_attr == record_id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def list_by_date_range(
        self,
        *,
        patient_id: str,
        from_dt: datetime.datetime,
        to_dt: datetime.datetime,
    ) -> list[DailyLog]:
        """List DailyLog rows for a patient within an inclusive datetime window.

        Both bounds are inclusive (``>=`` and ``<=``).  Rows are ordered by
        ``logged_at ASC``.

        Args:
            patient_id: The patient whose logs are in scope (required).
            from_dt:    Start of the window (naive UTC).
            to_dt:      End of the window (naive UTC).

        Returns:
            A list of DailyLog instances within the range, oldest first.
        """
        pid_attr = getattr(DailyLog, _PID)
        logged_at_attr = getattr(DailyLog, _LOGGED_AT)

        stmt = (
            select(DailyLog)
            .where(pid_attr == patient_id)
            .where(logged_at_attr >= from_dt)
            .where(logged_at_attr <= to_dt)
            .order_by(logged_at_attr.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
