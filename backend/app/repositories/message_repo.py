"""MessageRepository — patient-scoped access to Message rows.

Stack: SQLAlchemy 2.0 async (select() + session.execute()), SQLModel table models.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.repositories.base import PatientScopedRepository

# SQLModel generates mapped attributes whose __eq__ returns a Python bool at
# the Python level, but a ColumnElement at runtime.  mypy strict mode rejects
# Model.col == value in .where() because it infers bool.  We retrieve the
# attribute via getattr() (typed Any) so mypy accepts the expression while
# the generated SQL is identical.  This pattern mirrors the base repository.
_PID = "patient_id"
_CREATED_AT = "created_at"
_ID = "id"


class MessageRepository(PatientScopedRepository[Message]):
    """Async repository for Message — enforces patient_id isolation.

    Every query filters ``WHERE patient_id = :pid`` at the SQL level.
    Cross-patient reads are structurally impossible.

    Usage::

        repo = MessageRepository(session)
        msg = await repo.create(patient_id="PT0001", message=m)
        messages = await repo.list(patient_id="PT0001")
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Message)

    async def create(self, *, patient_id: str, message: Message) -> Message:
        """Persist a new Message row, defensively setting patient_id.

        Args:
            patient_id: The patient this message belongs to.
            message:    The Message instance to persist.

        Returns:
            The persisted Message instance with id populated.
        """
        # Defensive set — overwrites whatever the caller placed on the object.
        object.__setattr__(message, "patient_id", patient_id)
        self._session.add(message)
        await self._session.flush()
        return message

    async def get(  # type: ignore[override]
        self,
        *,
        patient_id: str,
        record_id: int,
    ) -> Message | None:
        """Fetch a single Message by patient_id + id.

        Returns ``None`` if the record does not exist or belongs to a
        different patient.

        Args:
            patient_id: The patient whose records are in scope.
            record_id:  The surrogate id of the Message.

        Returns:
            The matching Message, or ``None``.
        """
        pid_attr = getattr(Message, _PID)
        id_attr = getattr(Message, _ID)

        stmt = (
            select(Message)
            .where(pid_attr == patient_id)
            .where(id_attr == record_id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def list(  # type: ignore[override]
        self,
        *,
        patient_id: str,
    ) -> list[Message]:
        """List all messages for a patient, ordered by created_at ASC.

        Args:
            patient_id: The patient whose messages are in scope.

        Returns:
            A list of Message instances, oldest first (chronological order).
        """
        pid_attr = getattr(Message, _PID)
        created_at_attr = getattr(Message, _CREATED_AT)

        stmt = (
            select(Message)
            .where(pid_attr == patient_id)
            .order_by(created_at_attr.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
