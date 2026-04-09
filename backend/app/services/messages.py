"""MessagesService — stub list/post for patient ↔ care-team messages.

This is a persistence stub.  Messages are plain text; no attachment support
or read-receipt logic is implemented in the MVP.

Usage::

    from app.services.messages import MessagesService

    service = MessagesService(session=session)

    # Post a message
    msg = await service.post(
        patient_id="PT0001",
        content="Hello from the patient",
        sender="patient",
    )

    # List all messages (chronological order)
    thread = await service.list(patient_id="PT0001")
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.repositories.message_repo import MessageRepository


class MessagesService:
    """List and post in-app messages with hard patient_id scoping.

    Args:
        session: An open ``AsyncSession`` (injected by FastAPI / test fixture).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MessageRepository(session)

    async def list(self, *, patient_id: str) -> list[Message]:
        """Return all messages for a patient in chronological order.

        Delegates directly to ``MessageRepository.list``, which injects
        ``WHERE patient_id = :pid`` at the SQL level.

        Args:
            patient_id: The patient whose message thread is in scope.

        Returns:
            A list of ``Message`` instances ordered by ``created_at ASC``
            (oldest first — natural conversation order).
        """
        return await self._repo.list(patient_id=patient_id)

    async def post(
        self,
        *,
        patient_id: str,
        content: str,
        sender: str,
    ) -> Message:
        """Persist a new message in the patient's thread.

        The ``sender`` value must be either ``"patient"`` or ``"clinician"``.
        Patient isolation is enforced at the repository layer — the repo
        overwrites any ``patient_id`` on the model with the value supplied
        here, making cross-patient writes structurally impossible.

        Args:
            patient_id: The patient whose thread this message belongs to.
            content:    Plain-text message body.
            sender:     ``"patient"`` or ``"clinician"``.

        Returns:
            The persisted ``Message`` instance with ``id`` populated.
        """
        message = Message(
            patient_id=patient_id,
            sender=sender,
            content=content,
        )
        return await self._repo.create(patient_id=patient_id, message=message)
