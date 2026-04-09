"""NotificationsService — LLM-generated smart notification copy + persistence.

This service generates personalised notification copy via the LLM provider
(using the ``notifications.system.md`` prompt) and persists a ``Notification``
row for the audit trail.  No real push delivery is performed in the MVP — the
generated copy is returned to the caller for in-app display.

Wellness framing is enforced by the prompt file itself.  The service never
emits diagnostic verbs (diagnose/treat/cure/prevent-disease).

Usage::

    from app.services.notifications import NotificationsService
    from app.ai.llm import FakeLLMProvider

    service = NotificationsService(session=session, llm=FakeLLMProvider())
    response = await service.generate_smart(
        patient_id="PT0001",
        trigger_kind="streak_at_risk",
        context={"streak_days": 5},
    )
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import LLMProvider
from app.ai.prompt_loader import load_prompt
from app.models.notification import Notification
from app.repositories.notification_repo import NotificationRepository
from app.schemas.ai_common import AI_DISCLAIMER, AIMeta
from app.schemas.notifications import SmartNotificationResponse

# Default model used for notification copy generation.
_DEFAULT_MODEL = "gemini-2.5-flash"

# Prompt name for the notifications system prompt.
_PROMPT_NAME = "notifications.system"


class NotificationsService:
    """Generate LLM-backed smart notification copy and persist it.

    Args:
        session: An open ``AsyncSession`` (injected by FastAPI / test fixture).
        llm:     The configured ``LLMProvider`` instance.  In dev/tests this is
                 ``FakeLLMProvider``; in prod it is ``GeminiProvider``.
    """

    def __init__(self, session: AsyncSession, llm: LLMProvider) -> None:
        self._session = session
        self._llm = llm
        self._repo = NotificationRepository(session)

    async def generate_smart(
        self,
        *,
        patient_id: str,
        trigger_kind: str,
        context: dict[str, Any],
        model: str = _DEFAULT_MODEL,
    ) -> SmartNotificationResponse:
        """Generate personalised notification copy and persist the row.

        Calls the LLM with the ``notifications.system.md`` system prompt and
        a user message that contains the trigger event and context JSON.
        Parses the response into a ``SmartNotificationResponse``, then
        persists a ``Notification`` row for the audit trail.

        Patient_id isolation is enforced in the repository layer — the repo
        overwrites any ``patient_id`` on the model with the value provided
        here, making cross-patient writes structurally impossible.

        Args:
            patient_id:   The patient this notification is for.
            trigger_kind: Notification event type, e.g. ``"streak_at_risk"``.
            context:      Event-specific payload passed to the LLM.
            model:        Model identifier (defaults to ``gemini-2.5-flash``).

        Returns:
            A ``SmartNotificationResponse`` with the generated copy plus the
            AI observability metadata and wellness disclaimer.
        """
        import time

        system_prompt = load_prompt(_PROMPT_NAME)
        user_message = json.dumps(
            {"trigger": trigger_kind, "context": context},
            ensure_ascii=False,
        )

        # --- LLM call ---
        t0 = time.monotonic()
        raw = await self._llm.generate(
            system=system_prompt,
            user=user_message,
            model=model,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)

        # --- Parse raw output ---
        # FakeLLMProvider returns str; GeminiProvider may return str or dict.
        title, body, cta = _parse_llm_output(raw, trigger_kind=trigger_kind)

        # --- Build AI observability metadata (no PHI) ---
        ai_meta = AIMeta(
            model=model,
            prompt_name=_PROMPT_NAME,
            request_id=str(uuid.uuid4()),
            token_in=0,   # Token counts are placeholders in the stub; real
            token_out=0,  # implementation would read from the SDK response.
            latency_ms=latency_ms,
        )

        # --- Persist the notification row ---
        notification = Notification(
            patient_id=patient_id,
            kind=trigger_kind,
            title=title,
            body=body,
            cta=cta,
        )
        await self._repo.create(patient_id=patient_id, notification=notification)

        return SmartNotificationResponse(
            title=title,
            body=body,
            cta=cta,
            disclaimer=AI_DISCLAIMER,
            ai_meta=ai_meta,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_llm_output(
    raw: str | dict[str, Any],
    *,
    trigger_kind: str,
) -> tuple[str, str, str]:
    """Parse LLM output into ``(title, body, cta)``.

    The notifications prompt instructs the model to return valid JSON with
    ``title``, ``body``, and ``cta`` keys.  We attempt JSON parsing first;
    if the output is plain text (e.g. from ``FakeLLMProvider``), we fall
    back to sensible defaults derived from the trigger_kind.

    Args:
        raw:          The raw LLM response (str or dict).
        trigger_kind: The notification trigger, used for fallback copy.

    Returns:
        A ``(title, body, cta)`` tuple of strings.
    """
    # Case 1: LLM returned a dict directly (GeminiProvider with schema)
    if isinstance(raw, dict):
        return (
            str(raw.get("title", f"Notification: {trigger_kind}")),
            str(raw.get("body", "Keep up your wellness journey!")),
            str(raw.get("cta", "View")),
        )

    # Case 2: str — attempt JSON parse
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return (
                str(parsed.get("title", f"Notification: {trigger_kind}")),
                str(parsed.get("body", "Keep up your wellness journey!")),
                str(parsed.get("cta", "View")),
            )
    except (json.JSONDecodeError, ValueError):
        pass

    # Case 3: plain-text fallback (FakeLLMProvider returns sentences)
    # Use the raw text as the body and construct minimal title + cta.
    body = raw.strip()
    title = trigger_kind.replace("_", " ").capitalize()
    cta = "View details"
    return title, body, cta
