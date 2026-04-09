"""NotificationRepository — patient-scoped access to Notification rows.

Stack: SQLAlchemy 2.0 async (select() + session.execute()), SQLModel table models.
"""

from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.repositories.base import PatientScopedRepository

# SQLModel generates mapped attributes whose __eq__ returns a Python bool at
# the Python level, but a ColumnElement at runtime.  mypy strict mode rejects
# Model.col == value in .where() because it infers bool.  We retrieve the
# attribute via getattr() (typed Any) so mypy accepts the expression while
# the generated SQL is identical.  This pattern mirrors the base repository.
_PID = "patient_id"
_CREATED_AT = "created_at"
_READ_AT = "read_at"
_ID = "id"


class NotificationRepository(PatientScopedRepository[Notification]):
    """Async repository for Notification — enforces patient_id isolation.

    Every query filters ``WHERE patient_id = :pid`` at the SQL level.
    Cross-patient reads are structurally impossible.

    Usage::

        repo = NotificationRepository(session)
        notif = await repo.create(patient_id="PT0001", notification=n)
        notifs = await repo.list(patient_id="PT0001")
        updated = await repo.mark_read(patient_id="PT0001", notification_id=n.id)
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Notification)

    async def create(
        self, *, patient_id: str, notification: Notification
    ) -> Notification:
        """Persist a new Notification row, defensively setting patient_id.

        Args:
            patient_id:   The patient this notification belongs to.
            notification: The Notification instance to persist.

        Returns:
            The persisted Notification instance with id populated.
        """
        # Defensive set — overwrites whatever the caller placed on the object.
        object.__setattr__(notification, "patient_id", patient_id)
        self._session.add(notification)
        await self._session.flush()
        return notification

    async def list(  # type: ignore[override]
        self,
        *,
        patient_id: str,
    ) -> list[Notification]:
        """List all notifications for a patient, ordered by created_at DESC.

        Args:
            patient_id: The patient whose notifications are in scope.

        Returns:
            A list of Notification instances, newest first.
        """
        pid_attr = getattr(Notification, _PID)
        created_at_attr = getattr(Notification, _CREATED_AT)

        stmt = (
            select(Notification)
            .where(pid_attr == patient_id)
            .order_by(created_at_attr.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_read(
        self, *, patient_id: str, notification_id: int
    ) -> Notification | None:
        """Set ``read_at`` to the current naive UTC time for a notification.

        Confirms the notification belongs to ``patient_id`` before updating.
        Returns ``None`` if the notification does not exist or belongs to a
        different patient.

        Args:
            patient_id:      The patient whose notification is being updated.
            notification_id: The surrogate id of the Notification.

        Returns:
            The updated Notification, or ``None``.
        """
        pid_attr = getattr(Notification, _PID)
        id_attr = getattr(Notification, _ID)

        stmt = (
            select(Notification)
            .where(pid_attr == patient_id)
            .where(id_attr == notification_id)
        )
        result = await self._session.execute(stmt)
        notification = result.scalars().first()
        if notification is None:
            return None

        # Naive UTC — CLAUDE.md pattern.
        read_at = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        object.__setattr__(notification, "read_at", read_at)
        await self._session.flush()
        return notification
