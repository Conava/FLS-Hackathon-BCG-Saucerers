"""Future-Self Simulator service — LLM-backed biological-age projection.

Stateless — not persisted.  Takes a patient_id and lifestyle slider adjustments,
calls the ``future-self.system.md`` LLM prompt, and returns a
``FutureSelfResponse`` envelope containing a projected biological age and a
wellness-framed narrative comparing current vs improved trajectories.

Design:
  - ``project()`` is the primary entry point, called from the insights router.
  - The service accepts a ``session`` argument so it can be injected with the
    same ``AsyncSession`` used elsewhere in the request lifecycle (even though
    this service does not itself read/write DB rows today).
  - ``bio_age`` is extracted from the LLM output when structured output is
    available; for ``FakeLLMProvider`` we default to a reasonable sentinel (35)
    via the ``FutureSelfLLMOutput`` schema.

Usage::

    from app.services.future_self import FutureSelfService

    service = FutureSelfService(llm=get_llm_provider(settings), session=db_session)
    response = await service.project(
        patient_id="PT0001",
        sliders={"sleep_improvement": 2, "exercise_frequency": 3},
    )
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import LLMProvider
from app.ai.prompt_loader import load_prompt
from app.schemas.ai_common import AI_DISCLAIMER, AIMeta
from app.schemas.outlook import FutureSelfResponse

# Prompt file key passed to load_prompt(); the loader appends ".md" so the
# file on disk is "future-self.system.md".
_PROMPT_FILE = "future-self.system"

# Prompt name surfaced in ai_meta.prompt_name (human-readable, no ".system").
_PROMPT_NAME = "future-self"

# Default model identifier.  FakeLLMProvider ignores this.
_DEFAULT_MODEL = "gemini-2.5-flash"


# ---------------------------------------------------------------------------
# Structured output schema for the LLM call
# ---------------------------------------------------------------------------


class _FutureSelfLLMOutput(BaseModel):
    """Structured response from the future-self LLM prompt.

    Used as ``response_schema`` in ``LLMProvider.generate`` so the LLM returns
    a typed dict rather than freeform text.  ``FakeLLMProvider`` instantiates
    this schema with its defaults to produce deterministic output.
    """

    bio_age: int = Field(
        default=35,
        description="Projected biological age (years) given slider-adjusted lifestyle",
    )
    narrative: str = Field(
        default=(
            "Your current habits show strong potential. "
            "With the improvements you've outlined, research suggests you could maintain "
            "higher energy levels and vitality well into your later years. "
            "This is wellness guidance, not medical advice."
        ),
        description=(
            "3–5 sentence wellness-framed paragraph comparing current vs improved trajectory"
        ),
    )


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------


class FutureSelfService:
    """Projects a patient's future biological age and wellness narrative.

    Calls the ``future-self`` LLM prompt with the patient's current vitality
    snapshot and their slider-adjusted lifestyle target.  Returns a
    ``FutureSelfResponse`` envelope (disclaimer + ai_meta included).

    Args:
        llm:     An ``LLMProvider`` implementation.
        session: An open ``AsyncSession`` (injected; not currently used for
                 writes, but preserved for future patient-context enrichment).
    """

    def __init__(self, llm: LLMProvider, session: AsyncSession) -> None:
        self._llm = llm
        # session reserved for future context queries (e.g. VitalitySnapshot)
        self._session = session

    async def project(
        self,
        *,
        patient_id: str,
        sliders: dict[str, Any],
    ) -> FutureSelfResponse:
        """Generate a future-self projection for the given patient and sliders.

        Builds a user message from the ``patient_id`` and ``sliders``, invokes
        the LLM with ``response_schema=_FutureSelfLLMOutput`` for structured
        output, and wraps the result in a ``FutureSelfResponse`` envelope.

        Args:
            patient_id: The patient to project.
            sliders:    Lifestyle adjustment values, e.g.
                        ``{"sleep_improvement": 2, "exercise_frequency": 4}``.

        Returns:
            ``FutureSelfResponse`` with ``bio_age``, ``narrative``,
            ``disclaimer``, and ``ai_meta``.
        """
        system_prompt = load_prompt(_PROMPT_FILE)
        user_message = _build_future_self_user_message(patient_id=patient_id, sliders=sliders)

        t0 = time.monotonic()
        raw: Any = await self._llm.generate(
            system=system_prompt,
            user=user_message,
            model=_DEFAULT_MODEL,
            response_schema=_FutureSelfLLMOutput,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)

        # LLMProvider.generate returns dict when response_schema is provided.
        if isinstance(raw, dict):
            bio_age = int(raw.get("bio_age", 35))
            narrative = str(raw.get("narrative", "")).strip()
        else:
            # Fallback: plain text response
            bio_age = 35
            narrative = str(raw).strip()

        # Ensure narrative is non-empty
        if not narrative:
            narrative = _FutureSelfLLMOutput().narrative

        request_id = str(uuid.uuid4())
        ai_meta = AIMeta(
            model=_DEFAULT_MODEL,
            prompt_name=_PROMPT_NAME,
            request_id=request_id,
            token_in=0,    # TODO: wire real usage when GeminiProvider exposes it
            token_out=0,
            latency_ms=latency_ms,
        )

        return FutureSelfResponse(
            bio_age=bio_age,
            narrative=narrative,
            disclaimer=AI_DISCLAIMER,
            ai_meta=ai_meta,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_future_self_user_message(
    *,
    patient_id: str,
    sliders: dict[str, Any],
) -> str:
    """Construct the user message for the future-self LLM call.

    Note: ``patient_id`` is included only to give the prompt context — no PHI
    is written here.  Slider values are included as lifestyle adjustment targets.

    Args:
        patient_id: Patient identifier (for prompt context, not PHI logging).
        sliders:    Lifestyle slider adjustments keyed by dimension name.

    Returns:
        A plain-text user message string.
    """
    slider_lines = "\n".join(
        f"  - {key}: {value}" for key, value in sorted(sliders.items())
    )
    if not slider_lines:
        slider_lines = "  (no slider adjustments — baseline trajectory only)"

    return (
        f"Patient: {patient_id}\n\n"
        "Lifestyle slider adjustments (user's target improvements):\n"
        f"{slider_lines}\n\n"
        "Please project the patient's future biological age and provide a 3–5 sentence "
        "narrative comparing their current trajectory versus the slider-adjusted improved "
        "trajectory. Use the structured output format: bio_age (int) and narrative (str). "
        "Keep all language wellness-framed — no diagnostic verbs."
    )
