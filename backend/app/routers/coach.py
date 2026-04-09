"""SSE streaming router for the AI Health Coach.

Provides ``POST /patients/{patient_id}/coach/chat`` which streams a
conversational AI response as a Server-Sent Events (SSE) stream.

Architecture
------------
The endpoint delegates entirely to ``CoachService.stream()``, which assembles
patient context from the database and yields event dicts via an async generator.
This router wraps that generator in ``sse_starlette.EventSourceResponse`` for
the correct ``text/event-stream`` wire format.

SSE event format
----------------
Each event yielded to the client is in standard SSE format::

    event: token
    data: {"type": "token", "text": "chunk text"}

    event: done
    data: {"type": "done", "ai_meta": {...}, "disclaimer": "..."}

On error, a final error event is emitted and the stream closes cleanly::

    event: error
    data: {"type": "error", "message": "error description"}

PHI policy
----------
No patient name, email, or patient_id is logged anywhere in this module.
The ``CoachService`` itself enforces PHI-free logging.

Stack: FastAPI + sse_starlette + SQLAlchemy 2.0 async + ``FakeLLMProvider``
(in tests) / ``GeminiProvider`` (in production).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import api_key_auth
from app.db.session import get_session
from app.repositories.patient_repo import PatientRepository
from app.schemas.coach import CoachChatRequest

router = APIRouter(prefix="/patients", tags=["coach"])

# Dependency type aliases for concise route signatures.
_Session = Annotated[AsyncSession, Depends(get_session)]
_Auth = Annotated[None, Depends(api_key_auth)]


@router.post(
    "/{patient_id}/coach/chat",
    summary="Stream a conversational AI coach response via SSE",
    response_description="text/event-stream — SSE events: token*, done | error",
)
async def coach_chat(
    patient_id: str,
    request: CoachChatRequest,
    session: _Session,
    _auth: _Auth,
) -> EventSourceResponse:
    """Stream an AI Health Coach response for *patient_id*.

    The response is a ``text/event-stream`` SSE stream containing:
    - One or more ``token`` events (text chunks from the LLM).
    - One final ``done`` event with ``ai_meta`` and the wellness disclaimer.
    - On error: one ``error`` event followed by stream close.

    The ``patient_id`` path parameter is threaded into ``CoachService`` which
    scopes all database reads to that patient — ensuring cross-patient isolation.

    Args:
        patient_id: The patient's unique identifier (e.g. ``PT0001``).
        request:    Inbound JSON payload — ``message`` and optional ``history``.
        session:    Injected ``AsyncSession`` (per-request).
        _auth:      ``api_key_auth`` result (validates ``X-API-Key`` header).

    Returns:
        An ``EventSourceResponse`` that streams SSE events to the client.

    Raises:
        HTTPException 404: When *patient_id* does not exist in the database.
        HTTPException 401: When the ``X-API-Key`` header is absent or invalid
                           (raised by ``api_key_auth`` before this handler runs).
    """
    # Verify the patient exists before streaming — returning 404 before opening
    # the SSE stream gives a clean HTTP-level error that clients can handle.
    patient_repo = PatientRepository(session)
    patient = await patient_repo.get(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found.",
        )

    async def _event_generator() -> AsyncIterator[dict[str, Any]]:
        """Async generator that drives ``CoachService.stream()`` to SSE dicts.

        Yields dicts accepted by ``sse_starlette.EventSourceResponse``::

            {"event": "<type>", "data": "<json string>"}

        On exception, yields a final ``error`` event and stops.
        """
        from app.ai.llm import FakeLLMProvider, get_llm_provider
        from app.core.config import Settings
        from app.services.coach import CoachService

        settings = Settings()
        llm = get_llm_provider(settings)

        svc = CoachService(session=session, llm=llm)

        try:
            async for ev in svc.stream(
                patient_id=patient_id,
                message=request.message,
                history=request.history,
            ):
                yield {
                    "event": ev["type"],
                    "data": json.dumps(ev),
                }
        except Exception as exc:  # noqa: BLE001
            error_payload = {"type": "error", "message": str(exc)}
            yield {
                "event": "error",
                "data": json.dumps(error_payload),
            }

    return EventSourceResponse(_event_generator())
