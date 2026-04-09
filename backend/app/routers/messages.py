"""Messages router.

Provides two endpoints for in-app messaging between a patient and the care team.

Endpoints:
    GET  /patients/{patient_id}/messages  — list message thread
    POST /patients/{patient_id}/messages  — post a new message

Authentication:
    Every request must carry a valid ``X-API-Key`` header (enforced by
    ``api_key_auth``).

Isolation guarantee:
    The ``patient_id`` path parameter flows directly into
    ``MessagesService.list`` and ``MessagesService.post``, which hard-scope
    all reads and writes to the given patient.  Cross-patient access is
    structurally impossible at the repository layer.

Schema mapping note:
    The ``Message`` model uses ``created_at`` and ``sender`` as column names.
    The ``MessageOut`` schema (from T4) exposes ``sent_at`` and ``direction``
    for API consistency.  This router handles the mapping:
    - ``Message.created_at`` → ``MessageOut.sent_at``
    - ``Message.sender``     → ``MessageOut.direction`` (``"patient"`` →
      ``"inbound"``, anything else → ``"outbound"``)
    - ``MessageIn`` carries ``content`` and ``patient_id``; the router
      defaults ``sender`` to ``"patient"`` for inbound messages.
"""

from __future__ import annotations

import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import api_key_auth
from app.db.session import get_session
from app.models.message import Message
from app.repositories.patient_repo import PatientRepository
from app.schemas.messages import MessageIn
from app.services.messages import MessagesService

router = APIRouter(prefix="/patients", tags=["messages"])

# Type alias for the session dependency to keep signatures concise.
_Session = Annotated[AsyncSession, Depends(get_session)]
_Auth = Annotated[None, Depends(api_key_auth)]


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class MessageOut(BaseModel):
    """API response schema for a single persisted message.

    Maps ``Message.created_at`` → ``sent_at`` and ``Message.sender`` →
    ``direction`` (``"patient"`` → ``"inbound"``; other → ``"outbound"``).
    """

    model_config = ConfigDict(from_attributes=False)

    id: int = Field(..., description="Message primary key")
    patient_id: str = Field(..., description="Patient this message belongs to")
    content: str = Field(..., description="Message body text")
    sent_at: datetime.datetime = Field(
        ...,
        description="Timestamp when the message was sent (naive UTC)",
    )
    direction: Literal["inbound", "outbound"] = Field(
        ...,
        description="Message direction: 'inbound' (patient → app) or 'outbound' (app → patient)",
    )


class MessageListOut(BaseModel):
    """API response schema for a list of in-app messages."""

    model_config = ConfigDict(from_attributes=False)

    patient_id: str = Field(..., description="Patient the messages belong to")
    messages: list[MessageOut] = Field(
        default_factory=list,
        description="Messages ordered by sent_at ascending (chronological order)",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _map_message(msg: Message) -> MessageOut:
    """Convert a ``Message`` ORM instance to a ``MessageOut`` response schema.

    Maps:
    - ``created_at`` → ``sent_at``
    - ``sender``     → ``direction``
      (``"patient"`` → ``"inbound"``; any other value → ``"outbound"``)

    Args:
        msg: The ``Message`` ORM instance to convert.

    Returns:
        A ``MessageOut`` Pydantic model.
    """
    direction: Literal["inbound", "outbound"] = (
        "inbound" if msg.sender == "patient" else "outbound"
    )
    return MessageOut(
        id=msg.id,
        patient_id=msg.patient_id,
        content=msg.content,
        sent_at=msg.created_at,
        direction=direction,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{patient_id}/messages",
    response_model=MessageListOut,
    tags=["messages"],
    summary="List all in-app messages for a patient",
)
async def get_messages(
    patient_id: str,
    session: _Session,
    _auth: _Auth,
) -> MessageListOut:
    """Return all messages in the patient's thread, chronological order.

    The endpoint:
    1. Validates that the patient exists — returns 404 if not.
    2. Delegates to ``MessagesService.list`` which returns messages ordered
       by ``created_at ASC`` (oldest first — natural conversation order).
    3. Maps each ``Message`` ORM instance to ``MessageOut``.

    Isolation guarantee:
        The ``patient_id`` path parameter is the sole scope key.  No data from
        other patients can appear in the response.

    Args:
        patient_id: Path parameter — the patient whose thread to retrieve.
        session:    Injected ``AsyncSession`` (per-request).
        _auth:      ``api_key_auth`` result (validates ``X-API-Key`` header).

    Returns:
        ``MessageListOut`` with patient_id and messages list.

    Raises:
        HTTPException 404: If ``patient_id`` does not exist in the database.
    """
    patient_repo = PatientRepository(session)
    patient = await patient_repo.get(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found.",
        )

    service = MessagesService(session=session)
    messages = await service.list(patient_id=patient_id)

    return MessageListOut(
        patient_id=patient_id,
        messages=[_map_message(m) for m in messages],
    )


@router.post(
    "/{patient_id}/messages",
    response_model=MessageOut,
    tags=["messages"],
    summary="Post a new message in a patient's thread",
)
async def post_message(
    patient_id: str,
    body: MessageIn,
    session: _Session,
    _auth: _Auth,
) -> MessageOut:
    """Persist a new message and return it.

    The endpoint:
    1. Validates that the patient exists — returns 404 if not.
    2. Delegates to ``MessagesService.post`` with ``sender="patient"``
       (inbound direction — the patient or API caller is posting the message).
    3. Maps the persisted ``Message`` ORM instance to ``MessageOut``.

    Isolation guarantee:
        The ``patient_id`` path parameter is the sole scope key.  The service
        enforces ``patient_id`` scoping at the repository layer.

    Args:
        patient_id: Path parameter — the patient posting the message.
        body:       Request body with ``content`` (and optional ``patient_id``).
        session:    Injected ``AsyncSession`` (per-request).
        _auth:      ``api_key_auth`` result (validates ``X-API-Key`` header).

    Returns:
        ``MessageOut`` with id, patient_id, content, sent_at, and direction.

    Raises:
        HTTPException 404: If ``patient_id`` does not exist in the database.
    """
    patient_repo = PatientRepository(session)
    patient = await patient_repo.get(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found.",
        )

    service = MessagesService(session=session)
    # The POST endpoint always creates an inbound (patient-initiated) message.
    # The sender is set to "patient" which maps to direction="inbound".
    msg = await service.post(
        patient_id=patient_id,
        content=body.content,
        sender="patient",
    )

    return _map_message(msg)
