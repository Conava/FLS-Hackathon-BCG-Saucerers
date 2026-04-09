"""In-app message request/response DTOs.

``MessageIn`` is the inbound payload for posting a message.
``MessageOut`` is the response for a single persisted message.
``MessageListOut`` wraps the list returned by the history endpoint.

``direction`` uses a Literal type constrained to ``inbound`` (patient to app)
and ``outbound`` (app to patient), matching the values the Message model emits.
"""

from __future__ import annotations

import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MessageIn(BaseModel):
    """Inbound payload for ``POST /v1/messages``."""

    model_config = ConfigDict(from_attributes=True)

    patient_id: str = Field(..., description="Patient this message is addressed to or from")
    content: str = Field(..., description="Message body text")


class MessageOut(BaseModel):
    """API response schema for a single persisted message."""

    model_config = ConfigDict(from_attributes=True)

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

    model_config = ConfigDict(from_attributes=True)

    patient_id: str = Field(..., description="Patient the messages belong to")
    messages: list[MessageOut] = Field(
        default_factory=list,
        description="Messages ordered by sent_at descending",
    )
