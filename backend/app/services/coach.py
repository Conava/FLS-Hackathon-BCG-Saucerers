"""CoachService — conversational AI coach with SSE-friendly async streaming.

Architecture
------------
``CoachService.stream()`` assembles a rich context from four data sources, then
calls ``LLMProvider.generate_stream()`` to yield token-by-token events suitable
for Server-Sent Events (SSE).

Context assembly (in order)
1. **Profile summary** — Patient row + LifestyleProfile, summarised into a compact
   text block.
2. **Top-k EHR records** — up to ``EHR_TOPK`` records fetched via ``EHRRepository``.
   (Embedding-based similarity retrieval would go here in production; for this MVP
   we fall back to the most-recent N records since not all EHR rows are guaranteed
   to have embeddings.)
3. **Recent DailyLog** — last ``DAILY_LOG_WINDOW_DAYS`` days via
   ``DailyLogRepository.list_by_date_range``.
4. **Active Protocol** — the latest "active" protocol + its actions via
   ``ProtocolRepository.get_active`` / ``ProtocolActionRepository.list_for_patient``.

Event sequence
--------------
* ``{"type": "token", "text": "..."}`` — one per streamed chunk.
* ``{"type": "done", "ai_meta": {...}, "disclaimer": "..."}`` — final event.
  The ``done`` event always carries the wellness disclaimer.

PHI policy
----------
No patient name, email, or patient_id is logged.  Only ``request_id``,
``model``, ``prompt_name``, ``token_count`` (approximated from token events),
and ``latency_ms`` are emitted.

Stack: async generators, SQLAlchemy 2.0 async, SQLModel, ``google-genai`` via
the ``LLMProvider`` Protocol.
"""

from __future__ import annotations

import datetime
import time
import uuid
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompt_loader import load_prompt
from app.core.logging import get_logger
from app.repositories.daily_log_repo import DailyLogRepository
from app.repositories.ehr_repo import EHRRepository
from app.repositories.patient_repo import PatientRepository
from app.repositories.protocol_repo import ProtocolActionRepository, ProtocolRepository

if TYPE_CHECKING:
    from app.ai.llm import LLMProvider

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Model identifier used for the coach stream.
_COACH_MODEL = "gemini-2.5-pro"

#: How many EHR records to pull into the coach context window.
EHR_TOPK: int = 5

#: Number of days of daily logs to include.
DAILY_LOG_WINDOW_DAYS: int = 7

#: Wellness disclaimer embedded in every ``done`` event.
DISCLAIMER = (
    "Not medical advice. "
    "This AI-generated guidance is for informational and motivational purposes only. "
    "Always consult a qualified healthcare professional for medical decisions."
)

#: Prompt name for the coach system prompt (matches the .md file stem).
_PROMPT_NAME = "coach.system"

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# CoachService
# ---------------------------------------------------------------------------


class CoachService:
    """Streaming conversational coach service.

    Assembles patient context from multiple repositories and yields SSE-friendly
    event dicts via an async generator.

    Args:
        session: An open ``AsyncSession`` for database reads.
        llm:     An ``LLMProvider`` implementation — use ``FakeLLMProvider`` in
                 tests; ``GeminiProvider`` in production.

    Usage::

        svc = CoachService(session=session, llm=FakeLLMProvider())
        async for event in svc.stream(patient_id="PT0001", message="...", history=[]):
            # event is one of:
            #   {"type": "token", "text": "..."}
            #   {"type": "done", "ai_meta": {...}, "disclaimer": "..."}
            send_sse(event)
    """

    def __init__(self, session: AsyncSession, llm: LLMProvider) -> None:
        self._session = session
        self._llm = llm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def stream(
        self,
        patient_id: str,
        message: str,
        history: list[dict[str, Any]],
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield SSE-friendly events for a coach conversation turn.

        Assembles patient context, calls the LLM in streaming mode, and emits
        events in order:
          1. One ``token`` event per streamed chunk.
          2. One final ``done`` event with ``ai_meta`` and ``disclaimer``.

        Args:
            patient_id: The patient's unique identifier (e.g. ``"PT0001"``).
            message:    The user's latest message.
            history:    Prior conversation turns, each a dict with ``role`` and
                        ``content`` keys. May be empty for a new thread.

        Yields:
            Dicts with ``type`` in ``{"token", "done"}``.

        Raises:
            No exceptions are suppressed — any repository or LLM error propagates
            to the caller (the SSE router converts it to an ``error`` event).
        """
        request_id = str(uuid.uuid4())
        start_ts = time.monotonic()

        # 1. Assemble context — no PHI in the log call below.
        system_prompt = load_prompt(_PROMPT_NAME)
        user_prompt = await self._build_user_prompt(
            patient_id=patient_id,
            message=message,
            history=history,
        )

        token_count = 0

        # 2. Stream tokens from the LLM.
        async for chunk in self._llm.generate_stream(
            system=system_prompt,
            user=user_prompt,
            model=_COACH_MODEL,
        ):
            token_count += 1
            yield {"type": "token", "text": chunk}

        # 3. Emit the final done event.
        latency_ms = round((time.monotonic() - start_ts) * 1000)
        ai_meta = {
            "model": _COACH_MODEL,
            "prompt_name": _PROMPT_NAME,
            "request_id": request_id,
            "token_count": token_count,
            "latency_ms": latency_ms,
        }

        # PHI-free log — only request_id, model, prompt_name, token counts, latency.
        _logger.info(
            "coach stream complete",
            extra={
                "request_id": request_id,
                "model": _COACH_MODEL,
                "prompt_name": _PROMPT_NAME,
                "token_count": token_count,
                "latency_ms": latency_ms,
            },
        )

        yield {
            "type": "done",
            "ai_meta": ai_meta,
            "disclaimer": DISCLAIMER,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _build_user_prompt(
        self,
        patient_id: str,
        message: str,
        history: list[dict[str, Any]],
    ) -> str:
        """Assemble the user-side context block from all four data sources.

        The assembled prompt contains:
          - Patient biometrics and lifestyle summary.
          - Up to ``EHR_TOPK`` most-recent EHR records.
          - ``DAILY_LOG_WINDOW_DAYS`` days of daily logs.
          - The active protocol (name + actions).
          - Conversation history (last N turns).
          - The user's latest message.

        No raw patient identifiers (name, email) are included in log output.
        The prompt itself may contain PHI — that is expected — but it is never
        logged.

        Args:
            patient_id: Patient identifier used to scope all DB queries.
            message:    The user's latest message.
            history:    Prior conversation turns.

        Returns:
            A string containing the assembled user-side prompt.
        """
        parts: list[str] = []

        # ── 1. Profile summary ─────────────────────────────────────────────
        profile_block = await self._profile_summary(patient_id)
        if profile_block:
            parts.append(f"## Patient Profile\n{profile_block}")

        # ── 2. Top-k EHR records ───────────────────────────────────────────
        ehr_block = await self._ehr_context(patient_id)
        if ehr_block:
            parts.append(f"## Recent Health Records\n{ehr_block}")

        # ── 3. Recent daily logs ───────────────────────────────────────────
        log_block = await self._daily_log_context(patient_id)
        if log_block:
            parts.append(f"## Recent Daily Logs (last {DAILY_LOG_WINDOW_DAYS} days)\n{log_block}")

        # ── 4. Active protocol ─────────────────────────────────────────────
        protocol_block = await self._protocol_context(patient_id)
        if protocol_block:
            parts.append(f"## Active Wellness Protocol\n{protocol_block}")

        # ── 5. Conversation history ────────────────────────────────────────
        if history:
            history_lines = []
            for turn in history[-6:]:  # cap at 6 most-recent turns
                role = turn.get("role", "user")
                content = turn.get("content", "")
                history_lines.append(f"{role.capitalize()}: {content}")
            parts.append("## Conversation History\n" + "\n".join(history_lines))

        # ── 6. Current user message ────────────────────────────────────────
        parts.append(f"## User Message\n{message}")

        return "\n\n".join(parts)

    async def _profile_summary(self, patient_id: str) -> str:
        """Build a compact profile summary from Patient + LifestyleProfile.

        Returns an empty string if the patient row is not found (should not
        happen in production, but tests may seed partial data).
        """
        from sqlalchemy import select

        from app.models.lifestyle_profile import LifestyleProfile

        repo = PatientRepository(self._session)
        patient = await repo.get(patient_id=patient_id)
        if patient is None:
            return ""

        lines = [
            f"Age: {patient.age}, Sex: {patient.sex}, Country: {patient.country}",
        ]
        if patient.height_cm is not None and patient.weight_kg is not None:
            lines.append(f"Height: {patient.height_cm} cm, Weight: {patient.weight_kg} kg")
        if patient.bmi is not None:
            lines.append(f"BMI: {patient.bmi:.1f}")

        # Lifestyle profile (optional — may be absent for new patients)
        pid_attr = LifestyleProfile.patient_id
        stmt = select(LifestyleProfile).where(pid_attr == patient_id)
        result = await self._session.execute(stmt)
        lifestyle = result.scalars().first()

        if lifestyle is not None:
            if lifestyle.smoking_status:
                lines.append(f"Smoking: {lifestyle.smoking_status}")
            if lifestyle.diet_quality_score is not None:
                lines.append(f"Diet quality (self-rated): {lifestyle.diet_quality_score}/10")
            if lifestyle.exercise_sessions_weekly is not None:
                lines.append(
                    f"Exercise: {lifestyle.exercise_sessions_weekly} sessions/week"
                )
            if lifestyle.stress_level is not None:
                lines.append(f"Stress level: {lifestyle.stress_level}/10")
            if lifestyle.sleep_satisfaction is not None:
                lines.append(f"Sleep satisfaction: {lifestyle.sleep_satisfaction}/10")

        return "\n".join(lines)

    async def _ehr_context(self, patient_id: str) -> str:
        """Return a text block summarising the top-k most-recent EHR records.

        In production this would use embedding-based similarity (cosine distance
        on the query embedding vs. ``ehr_record.embedding``).  For MVP we simply
        take the ``EHR_TOPK`` most-recent rows — ordered by ``recorded_at DESC``
        already provided by ``EHRRepository.list``.
        """

        import json

        repo = EHRRepository(self._session)
        records = await repo.list(patient_id=patient_id)
        records = records[:EHR_TOPK]

        if not records:
            return ""

        lines: list[str] = []
        for rec in records:
            try:
                payload_str = json.dumps(rec.payload, ensure_ascii=False)
            except (TypeError, ValueError):
                payload_str = str(rec.payload)
            lines.append(f"[ref:{rec.id}] {rec.record_type}: {payload_str}")

        return "\n".join(lines)

    async def _daily_log_context(self, patient_id: str) -> str:
        """Return a text summary of the last ``DAILY_LOG_WINDOW_DAYS`` daily logs."""
        repo = DailyLogRepository(self._session)
        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        window_start = now - datetime.timedelta(days=DAILY_LOG_WINDOW_DAYS)

        logs = await repo.list_by_date_range(
            patient_id=patient_id,
            from_dt=window_start,
            to_dt=now,
        )

        if not logs:
            return ""

        lines: list[str] = []
        for log in logs:
            date_str = log.logged_at.strftime("%Y-%m-%d")
            parts: list[str] = [f"{date_str}:"]
            if log.mood is not None:
                parts.append(f"mood={log.mood}/5")
            if log.workout_minutes is not None:
                parts.append(f"workout={log.workout_minutes}min")
            if log.sleep_hours is not None:
                parts.append(f"sleep={log.sleep_hours}h")
            if log.water_ml is not None:
                parts.append(f"water={log.water_ml}ml")
            if log.alcohol_units is not None and log.alcohol_units > 0:
                parts.append(f"alcohol={log.alcohol_units}units")
            lines.append(" ".join(parts))

        return "\n".join(lines)

    async def _protocol_context(self, patient_id: str) -> str:
        """Return a text summary of the active protocol and its actions."""
        proto_repo = ProtocolRepository(self._session)
        action_repo = ProtocolActionRepository(self._session)

        protocol = await proto_repo.get_active(patient_id=patient_id)
        if protocol is None:
            return ""

        actions = await action_repo.list_for_patient(patient_id=patient_id)
        # Filter to only actions belonging to the active protocol.
        active_actions = [a for a in actions if a.protocol_id == protocol.id]

        lines: list[str] = [
            f"Status: {protocol.status}, Week: {protocol.week_start}",
        ]
        for action in active_actions:
            streak = f"streak={action.streak_days}d"
            done = "✓" if action.completed_today else "○"
            lines.append(
                f"  {done} [{action.category}] {action.title} "
                f"({action.target_value or 'no target'}) {streak}"
            )

        return "\n".join(lines)
