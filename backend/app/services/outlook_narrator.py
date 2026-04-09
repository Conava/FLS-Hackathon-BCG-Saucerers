"""Outlook Narrator service — LLM-backed narrative for Vitality Outlook.

Converts a computed ``VitalityOutlook`` row into a single motivating sentence
using the ``outlook-narrator`` system prompt.  Persists the narrative back into
the ``VitalityOutlook`` row via ``VitalityOutlookRepository.upsert_by_horizon``.

Design:
  - ``narrate()`` is the primary entry point (called on login or after a
    protocol-action completion).
  - Persistence responsibility lives **here** (not in the router) because the
    router may call narrate as a fire-and-forget side-effect and the test suite
    needs to assert DB state without a running HTTP server.
  - ``ai_meta`` is populated with heuristic token estimates since ``FakeLLMProvider``
    does not return real usage stats; real usage is wired when ``GeminiProvider`` is
    extended with usage metadata.

Usage::

    from app.services.outlook_narrator import OutlookNarratorService

    service = OutlookNarratorService(llm=get_llm_provider(settings), session=db_session)
    response = await service.narrate(patient_id="PT0001", outlook=vitality_outlook_row)
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import LLMProvider
from app.ai.prompt_loader import load_prompt
from app.models.vitality_outlook import VitalityOutlook
from app.repositories.outlook_repo import VitalityOutlookRepository
from app.schemas.ai_common import AIMeta
from app.schemas.outlook import OutlookNarratorResponse

# Prompt file key passed to load_prompt(); the loader appends ".md" so the
# file on disk is "outlook-narrator.system.md".
_PROMPT_FILE = "outlook-narrator.system"

# Prompt name surfaced in ai_meta.prompt_name (human-readable, no ".system").
_PROMPT_NAME = "outlook-narrator"

# Default model identifier used by the Gemini provider.
# FakeLLMProvider ignores this value; GeminiProvider routes to Gemini Flash.
_DEFAULT_MODEL = "gemini-2.5-flash"


class OutlookNarratorService:
    """Generates a one-sentence wellness narrative for a VitalityOutlook.

    Loads the ``outlook-narrator.system.md`` prompt, calls the injected
    ``LLMProvider.generate``, then persists the narrative to the DB via
    ``VitalityOutlookRepository.upsert_by_horizon``.

    Args:
        llm:     An ``LLMProvider`` implementation (``FakeLLMProvider`` in tests,
                 ``GeminiProvider`` in production).
        session: An open ``AsyncSession`` scoped to the current request / test.
    """

    def __init__(self, llm: LLMProvider, session: AsyncSession) -> None:
        self._llm = llm
        self._repo = VitalityOutlookRepository(session)

    async def narrate(
        self,
        *,
        patient_id: str,
        outlook: VitalityOutlook,
    ) -> OutlookNarratorResponse:
        """Generate a narrative for the given VitalityOutlook and persist it.

        Builds a user message from the outlook fields, calls the LLM, wraps
        the response in ``OutlookNarratorResponse``, and upserts the narrative
        into the ``VitalityOutlook`` row.

        Args:
            patient_id: The patient this outlook belongs to.
            outlook:    The ``VitalityOutlook`` row to narrate.

        Returns:
            An ``OutlookNarratorResponse`` with ``narrative``, ``disclaimer``,
            and ``ai_meta`` fields populated.
        """
        system_prompt = load_prompt(_PROMPT_FILE)
        user_message = _build_narrator_user_message(outlook)

        t0 = time.monotonic()
        raw: Any = await self._llm.generate(
            system=system_prompt,
            user=user_message,
            model=_DEFAULT_MODEL,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)

        # LLMProvider.generate returns str when response_schema is None.
        narrative: str = str(raw).strip() if raw else ""

        request_id = str(uuid.uuid4())
        ai_meta = AIMeta(
            model=_DEFAULT_MODEL,
            prompt_name=_PROMPT_NAME,
            request_id=request_id,
            token_in=0,    # TODO: wire real usage when GeminiProvider exposes it
            token_out=0,
            latency_ms=latency_ms,
        )

        # Persist the narrative back into the VitalityOutlook row.
        from datetime import UTC, datetime

        updated_outlook = VitalityOutlook(
            id=outlook.id,
            patient_id=patient_id,
            horizon_months=outlook.horizon_months,
            projected_score=outlook.projected_score,
            narrative=narrative,
            computed_at=datetime.now(UTC).replace(tzinfo=None),
        )
        await self._repo.upsert_by_horizon(patient_id=patient_id, outlook=updated_outlook)

        from app.schemas.ai_common import AI_DISCLAIMER

        return OutlookNarratorResponse(
            narrative=narrative,
            disclaimer=AI_DISCLAIMER,
            ai_meta=ai_meta,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_narrator_user_message(outlook: VitalityOutlook) -> str:
    """Construct the user message from outlook fields for the narrator LLM call.

    Summarises the outlook row into a brief structured prompt that lets the
    LLM produce a focused one-sentence narrative without fabricating numbers.

    Args:
        outlook: The VitalityOutlook row to narrate.

    Returns:
        A plain-text user message string.
    """
    return (
        f"Current Vitality Score: {outlook.projected_score:.1f}\n"
        f"Forecast horizon: {outlook.horizon_months} months\n"
        f"Projected score at horizon: {outlook.projected_score:.1f}\n"
        f"Existing narrative (if any): {outlook.narrative}\n\n"
        "Please write a single motivating sentence (max 25 words) for the user's "
        "Vitality Outlook screen, referencing the projected score and at least one "
        "driver category. No markdown, no bullet points, no line breaks."
    )
