"""Coach chat request/response DTOs.

``CoachChatRequest`` is the inbound payload for ``POST /v1/patients/{pid}/coach/chat``.
``CoachEvent`` models each Server-Sent Event emitted by the streaming endpoint.

Event types:
- ``token``: a text chunk from the LLM stream
- ``protocol_suggestion``: a structured action suggestion the UI can offer to persist
- ``done``: final event carrying ``ai_meta`` for observability
- ``error``: emitted when streaming fails; the connection closes cleanly after this
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CoachChatRequest(BaseModel):
    """Inbound payload for the AI Health Coach streaming endpoint.

    ``history`` is a list of prior turns supplied by the client so the LLM
    can maintain conversation continuity without server-side session state.
    Each entry is a free-form dict with at minimum ``role`` and ``content`` keys.
    """

    model_config = ConfigDict(from_attributes=True)

    message: str = Field(..., description="The user's current message to the coach")
    history: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Prior conversation turns. Each dict must contain 'role' (user|assistant) "
            "and 'content' (str). Maximum 50 turns recommended."
        ),
    )


class CoachEvent(BaseModel):
    """A single Server-Sent Event in the coach streaming response.

    The ``type`` discriminator drives client-side rendering:
    - ``token``: render ``payload`` as a text chunk
    - ``protocol_suggestion``: show a confirmation card to the user
    - ``done``: streaming complete; ``payload`` may carry ``ai_meta`` dict
    - ``error``: surface to user; stream terminates
    """

    model_config = ConfigDict(from_attributes=True)

    type: Literal["token", "protocol_suggestion", "done", "error"] = Field(
        ...,
        description="Event discriminator: token | protocol_suggestion | done | error",
    )
    payload: Any = Field(
        default=None,
        description=(
            "Event payload. Type depends on 'type': "
            "str for token/error, dict for protocol_suggestion/done."
        ),
    )
