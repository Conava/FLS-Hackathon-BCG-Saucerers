"""Smart notification router.

Provides a single endpoint that generates personalised notification copy via
the LLM provider and persists the notification row.

Endpoint:
    POST /patients/{patient_id}/notifications/smart

Authentication:
    Every request must carry a valid ``X-API-Key`` header (enforced by
    ``api_key_auth``).

Isolation guarantee:
    The ``patient_id`` path parameter flows directly into
    ``NotificationsService.generate_smart`` which hard-scopes writes and reads
    to the given patient.  Cross-patient writes are structurally impossible.

PHI policy:
    No patient-identifiable information is written to logs.  Only
    ``request_id``, ``model``, ``prompt_name``, ``token_in``, ``token_out``,
    and ``latency_ms`` are emitted by ``NotificationsService``.

Dependency injection:
    ``get_notifications_service`` is a FastAPI dependency factory.  Tests
    override it to inject a ``FakeLLMProvider``-backed ``NotificationsService``
    so no real Gemini calls are made during the test suite.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import LLMProvider, get_llm_provider
from app.core.config import Settings
from app.core.security import api_key_auth
from app.db.session import get_session
from app.repositories.patient_repo import PatientRepository
from app.schemas.notifications import SmartNotificationRequest, SmartNotificationResponse
from app.services.notifications import NotificationsService

router = APIRouter(prefix="/patients", tags=["notifications"])

# Type alias for the session dependency to keep signatures concise.
_Session = Annotated[AsyncSession, Depends(get_session)]
_Auth = Annotated[None, Depends(api_key_auth)]


# ---------------------------------------------------------------------------
# NotificationsService dependency factory
# ---------------------------------------------------------------------------


def get_notifications_service(session: _Session) -> NotificationsService:
    """FastAPI dependency that creates a ``NotificationsService`` backed by the configured LLM.

    Reads ``llm_provider`` from ``Settings`` to decide which ``LLMProvider``
    implementation to use.  In tests this dependency is overridden to inject a
    ``FakeLLMProvider``-backed ``NotificationsService`` — no real Gemini calls are made.

    Args:
        session: The injected ``AsyncSession`` for this request.

    Returns:
        A ``NotificationsService`` ready to generate and persist notifications.
    """
    settings = Settings()
    llm: LLMProvider = get_llm_provider(settings)
    return NotificationsService(session=session, llm=llm)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/{patient_id}/notifications/smart",
    response_model=SmartNotificationResponse,
    tags=["notifications"],
    summary="Generate and persist a smart notification using LLM copy generation",
)
async def post_smart_notification(
    patient_id: str,
    body: SmartNotificationRequest,
    session: _Session,
    _auth: _Auth,
    notifications_service: Annotated[NotificationsService, Depends(get_notifications_service)],
) -> SmartNotificationResponse:
    """Generate personalised notification copy and persist the row.

    The endpoint:
    1. Validates that the patient exists — returns 404 if not.
    2. Delegates to ``NotificationsService.generate_smart`` which calls the LLM
       with the ``notifications.system.md`` system prompt, parses the response
       into title/body/cta copy, persists a ``Notification`` row for the audit
       trail, and returns a ``SmartNotificationResponse``.

    Isolation guarantee:
        The ``patient_id`` path parameter is the sole scope key.  Notification
        rows are scoped to ``patient_id`` at the repository layer — no data from
        other patients can appear in the response.

    Args:
        patient_id:            Path parameter — the patient to notify, e.g. ``PT0282``.
        body:                  Request body with ``trigger_kind`` and ``context``.
        session:               Injected ``AsyncSession`` (per-request).
        _auth:                 ``api_key_auth`` result (validates ``X-API-Key`` header).
        notifications_service: Injected ``NotificationsService`` (overridable for tests).

    Returns:
        ``SmartNotificationResponse`` with generated title, body, cta, disclaimer,
        and ai_meta.

    Raises:
        HTTPException 404: If ``patient_id`` does not exist in the database.
    """
    # Guard: patient must exist before generating a notification.
    patient_repo = PatientRepository(session)
    patient = await patient_repo.get(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found.",
        )

    return await notifications_service.generate_smart(
        patient_id=patient_id,
        trigger_kind=body.trigger_kind,
        context=body.context,
    )
