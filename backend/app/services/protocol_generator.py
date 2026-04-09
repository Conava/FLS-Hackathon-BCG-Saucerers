"""ProtocolGeneratorService — structured LLM protocol generation with persistence.

Flow:
  1. Load ``LifestyleProfile`` for the patient (required — ValueError if missing).
  2. Load latest ``VitalitySnapshot`` (optional, included in context when present).
  3. Load last-7-day ``DailyLog`` entries and summarise adherence.
  4. Build a context string from all of the above.
  5. Call ``LLMProvider.generate`` with ``protocol-generator.system.md`` and
     ``response_schema=GeneratedProtocol``.
  6. Validate the returned dict via ``GeneratedProtocol.model_validate``.
  7. Hard-fail (``ValueError``) if:
       - actions list is empty or has more than 7 items
       - sum of parseable estimated minutes from action targets exceeds
         ``time_budget_minutes_per_day``
  8. Persist ``Protocol`` + one ``ProtocolAction`` per action via repositories.
  9. Return the persisted ``Protocol``.

Stack: FastAPI + SQLModel + SQLAlchemy 2.0 async + Pydantic v2 + google-genai
       via LLMProvider (see docs/09-ai-assist-playbook.md).

PHI policy: no patient name or free-text fields are logged.  Only request_id,
model, prompt_name, token counts and latency are emitted.
"""

from __future__ import annotations

import datetime
import logging
import re
from typing import TYPE_CHECKING, Any

from app.ai.prompt_loader import load_prompt
from app.core.logging import get_logger
from app.models.protocol import Protocol, ProtocolAction
from app.schemas.protocol import GeneratedProtocol

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.ai.llm import LLMProvider
    from app.models.daily_log import DailyLog
    from app.models.lifestyle_profile import LifestyleProfile
    from app.models.vitality_snapshot import VitalitySnapshot
    from app.repositories.protocol_repo import (
        ProtocolActionRepository,
        ProtocolRepository,
    )

_logger: logging.Logger = get_logger(__name__)

#: LLM model for protocol generation (docs/06-ai-layer.md)
_PROTOCOL_MODEL = "gemini-2.5-pro"

#: Prompt name (matches prompts/<name>.md)
_PROMPT_NAME = "protocol-generator.system"

#: Default time budget in minutes when none is specified on LifestyleProfile.
#: Using a large default so the constraint is skipped gracefully when
#: time_budget_minutes_per_day has not been set by the patient.
_DEFAULT_TIME_BUDGET_MINUTES: int = 120

#: Number of days of DailyLog history to include in adherence summary.
_LOG_LOOKBACK_DAYS: int = 7


# ---------------------------------------------------------------------------
# Minute parser — extracts estimated minutes from action target strings
# ---------------------------------------------------------------------------


def _parse_minutes_from_target(target: str) -> int:
    """Extract a minute count from an action target string.

    Looks for patterns like "30 min", "25 minutes", "1 hour 30 min", etc.
    Falls back to 0 when no parseable duration is found.

    Args:
        target: Measurable target string, e.g. ``"30 min brisk walk"``.

    Returns:
        Estimated minutes as a non-negative integer.
    """
    total = 0

    # Match hours: "1 hour", "2 hours", "1h"
    hour_match = re.search(r"(\d+)\s*h(?:our)?s?", target, re.IGNORECASE)
    if hour_match:
        total += int(hour_match.group(1)) * 60

    # Match minutes: "30 min", "30 minutes", "30m"
    min_match = re.search(r"(\d+)\s*m(?:in(?:ute)?s?)?(?:\b|$)", target, re.IGNORECASE)
    if min_match:
        total += int(min_match.group(1))

    return total


# ---------------------------------------------------------------------------
# Context builder — pure function, easy to test
# ---------------------------------------------------------------------------


def _build_user_context(
    patient_id: str,
    lifestyle: "LifestyleProfile",
    snapshot: "VitalitySnapshot | None",
    daily_logs: "list[DailyLog]",
) -> str:
    """Build the user-side context string for the protocol generator prompt.

    Assembles a structured text block from:
    - ``LifestyleProfile`` fields (goals, constraints, budget, diet)
    - Latest ``VitalitySnapshot`` sub-scores
    - 7-day ``DailyLog`` adherence summary (workout minutes, mood, sleep)

    Args:
        patient_id: Patient identifier (not included in output — PHI-free logs).
        lifestyle:  The patient's lifestyle profile row.
        snapshot:   Latest vitality snapshot, or ``None`` if not yet computed.
        daily_logs: Up to 7 days of daily logs for adherence summary.

    Returns:
        A multi-line context string ready to be passed as the ``user`` argument
        to ``LLMProvider.generate``.
    """
    lines: list[str] = ["## Patient Context for Protocol Generation\n"]

    # LifestyleProfile block
    lines.append("### Lifestyle Profile")
    time_budget = getattr(lifestyle, "time_budget_minutes_per_day", None)
    lines.append(f"- time_budget_minutes_per_day: {time_budget or 'not set'}")

    budget_eur = getattr(lifestyle, "out_of_pocket_budget_eur_per_month", None)
    lines.append(f"- out_of_pocket_budget_eur_per_month: {budget_eur or 'not set'}")

    diet = getattr(lifestyle, "dietary_restrictions", None)
    lines.append(f"- dietary_restrictions: {diet or 'none'}")

    allergies = getattr(lifestyle, "known_allergies", None)
    lines.append(f"- known_allergies: {allergies or 'none'}")

    injuries = getattr(lifestyle, "injuries_or_limitations", None)
    lines.append(f"- injuries_or_limitations: {injuries or 'none'}")

    # Extra available fields
    if lifestyle.exercise_sessions_weekly is not None:
        lines.append(f"- exercise_sessions_weekly: {lifestyle.exercise_sessions_weekly}")
    if lifestyle.sedentary_hrs_day is not None:
        lines.append(f"- sedentary_hrs_day: {lifestyle.sedentary_hrs_day}")
    if lifestyle.sleep_satisfaction is not None:
        lines.append(f"- sleep_satisfaction: {lifestyle.sleep_satisfaction}/10")
    if lifestyle.stress_level is not None:
        lines.append(f"- stress_level: {lifestyle.stress_level}/10")
    if lifestyle.diet_quality_score is not None:
        lines.append(f"- diet_quality_score: {lifestyle.diet_quality_score}/10")
    lines.append("")

    # VitalitySnapshot block
    if snapshot is not None:
        lines.append("### Latest Vitality Snapshot")
        lines.append(f"- composite_score: {snapshot.score:.1f}/100")
        for key, val in snapshot.subscores.items():
            lines.append(f"- {key}: {val}")
        if snapshot.risk_flags:
            lines.append(f"- flagged_areas: {list(snapshot.risk_flags.keys())}")
        lines.append("")
    else:
        lines.append("### Latest Vitality Snapshot\n- Not yet computed.\n")

    # DailyLog adherence summary
    lines.append("### 7-Day Adherence Summary (daily logs)")
    if daily_logs:
        total_workout = sum(
            (log.workout_minutes or 0) for log in daily_logs
        )
        avg_mood = (
            sum((log.mood or 0) for log in daily_logs if log.mood is not None)
            / max(1, sum(1 for log in daily_logs if log.mood is not None))
        )
        avg_sleep = (
            sum((log.sleep_hours or 0.0) for log in daily_logs if log.sleep_hours is not None)
            / max(1, sum(1 for log in daily_logs if log.sleep_hours is not None))
        )
        lines.append(f"- days_logged: {len(daily_logs)}")
        lines.append(f"- total_workout_minutes: {total_workout}")
        lines.append(f"- avg_mood: {avg_mood:.1f}/5")
        lines.append(f"- avg_sleep_hours: {avg_sleep:.1f}")
    else:
        lines.append("- No daily logs in the last 7 days.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ProtocolGeneratorService:
    """Generates and persists a weekly wellness protocol via LLM structured output.

    Depends on:
    - ``LLMProvider`` — for the LLM call
    - ``ProtocolRepository`` — for Protocol rows
    - ``ProtocolActionRepository`` — for ProtocolAction rows
    - ``AsyncSession`` — for context loading (LifestyleProfile, VitalitySnapshot,
      DailyLog) when not using the injectable ``_context_provider``

    The ``session`` argument is optional for unit tests: tests inject a
    ``_context_provider`` instead so no real DB is needed.

    Usage::

        svc = ProtocolGeneratorService(
            llm_provider=llm,
            protocol_repo=ProtocolRepository(session),
            action_repo=ProtocolActionRepository(session),
            session=session,
        )
        protocol = await svc.generate_for_patient("PT0001")
    """

    def __init__(
        self,
        *,
        llm_provider: "LLMProvider",
        protocol_repo: "ProtocolRepository",
        action_repo: "ProtocolActionRepository",
        session: "AsyncSession | None" = None,
    ) -> None:
        self._llm = llm_provider
        self._protocol_repo = protocol_repo
        self._action_repo = action_repo
        self._session = session
        # Injected by unit tests to avoid real DB context loading
        self._context_provider: "_FakeContextProvider | None" = None  # type: ignore[name-defined]

    async def generate_for_patient(self, patient_id: str) -> Protocol:
        """Generate and persist a new weekly protocol for the given patient.

        Steps:
        1. Load context (LifestyleProfile + VitalitySnapshot + DailyLog).
        2. Load system prompt from ``protocol-generator.system.md``.
        3. Call LLM with structured ``GeneratedProtocol`` schema.
        4. Validate + enforce hard constraints.
        5. Persist ``Protocol`` row and one ``ProtocolAction`` per action.
        6. Return the persisted ``Protocol``.

        Args:
            patient_id: The patient to generate a protocol for.

        Returns:
            The persisted ``Protocol`` instance (id is populated).

        Raises:
            ValueError: If ``LifestyleProfile`` is missing, actions list is
                empty or has more than 7 items, or total estimated time exceeds
                ``time_budget_minutes_per_day``.
        """
        # ------------------------------------------------------------------ #
        # Step 1: Load context                                                #
        # ------------------------------------------------------------------ #
        lifestyle, snapshot, daily_logs = await self._load_context(patient_id)

        if lifestyle is None:
            raise ValueError(
                f"LifestyleProfile not found for patient {patient_id!r}. "
                "Cannot generate protocol without lifestyle data."
            )

        # ------------------------------------------------------------------ #
        # Step 2: Build user context string                                   #
        # ------------------------------------------------------------------ #
        user_context = _build_user_context(
            patient_id=patient_id,
            lifestyle=lifestyle,
            snapshot=snapshot,
            daily_logs=daily_logs,
        )

        # ------------------------------------------------------------------ #
        # Step 3: Call LLM                                                    #
        # ------------------------------------------------------------------ #
        system_prompt = load_prompt(_PROMPT_NAME)
        raw_result = await self._llm.generate(
            system=system_prompt,
            user=user_context,
            model=_PROTOCOL_MODEL,
            response_schema=GeneratedProtocol,
        )

        _logger.info(
            "protocol_generator_llm_called",
            extra={"model": _PROTOCOL_MODEL, "prompt_name": _PROMPT_NAME},
        )

        # ------------------------------------------------------------------ #
        # Step 4: Validate with Pydantic                                      #
        # ------------------------------------------------------------------ #
        if not isinstance(raw_result, dict):
            raw_result = {}

        generated = GeneratedProtocol.model_validate(raw_result)

        # Hard constraint 1: action count 1–7
        action_count = len(generated.actions)
        if action_count == 0:
            raise ValueError(
                f"LLM returned 0 actions; protocol must have at least 1 action. "
                f"(Hard constraint: actions list must not be empty)"
            )
        if action_count > 7:
            raise ValueError(
                f"LLM returned {action_count} actions; maximum is 7. "
                f"(Hard constraint: actions list must have at most 7 items)"
            )

        # Hard constraint 2: time budget
        time_budget = getattr(lifestyle, "time_budget_minutes_per_day", None)
        if time_budget is not None:
            total_minutes = sum(
                _parse_minutes_from_target(action.target)
                for action in generated.actions
            )
            if total_minutes > time_budget:
                raise ValueError(
                    f"Actions total {total_minutes} minutes but "
                    f"time_budget_minutes_per_day is {time_budget}. "
                    f"(Hard constraint: total protocol time must fit within budget)"
                )

        # ------------------------------------------------------------------ #
        # Step 5: Persist Protocol row                                        #
        # ------------------------------------------------------------------ #
        today = datetime.date.today()
        # ISO week starts on Monday — find the Monday of this week
        week_start = today - datetime.timedelta(days=today.weekday())

        protocol = Protocol(
            patient_id=patient_id,
            week_start=week_start,
            status="active",
            generated_by=_PROTOCOL_MODEL,
        )
        persisted_protocol = await self._protocol_repo.create(
            patient_id=patient_id,
            protocol=protocol,
        )

        # ------------------------------------------------------------------ #
        # Step 6: Persist one ProtocolAction per generated action             #
        # ------------------------------------------------------------------ #
        for gen_action in generated.actions:
            action = ProtocolAction(
                protocol_id=persisted_protocol.id,  # type: ignore[arg-type]
                category=gen_action.category,
                title=gen_action.title,
                rationale=gen_action.rationale,
                target_value=gen_action.target,
                streak_days=0,
                completed_today=False,
            )
            await self._action_repo.add(action=action)

        _logger.info(
            "protocol_generated",
            extra={
                "protocol_id": persisted_protocol.id,
                "action_count": len(generated.actions),
                "model": _PROTOCOL_MODEL,
            },
        )

        return persisted_protocol

    # ---------------------------------------------------------------------- #
    # Internal helpers                                                         #
    # ---------------------------------------------------------------------- #

    async def _load_context(
        self, patient_id: str
    ) -> tuple[
        "LifestyleProfile | None",
        "VitalitySnapshot | None",
        "list[DailyLog]",
    ]:
        """Load context data for the given patient.

        In unit tests, a ``_context_provider`` is injected and used directly.
        In production, loads from the real DB via ``AsyncSession``.

        Args:
            patient_id: The patient to load context for.

        Returns:
            Tuple of ``(lifestyle, snapshot, daily_logs)``.
        """
        # Unit-test injection point — avoids real DB in unit tests
        if self._context_provider is not None:
            cp = self._context_provider
            return (
                getattr(cp, "lifestyle", None),
                getattr(cp, "snapshot", None),
                getattr(cp, "daily_logs", []),
            )

        # Production path — real DB session required
        if self._session is None:
            raise RuntimeError(
                "ProtocolGeneratorService requires either a real AsyncSession "
                "or an injected _context_provider."
            )

        return await self._load_context_from_db(patient_id)

    async def _load_context_from_db(
        self, patient_id: str
    ) -> tuple[
        "LifestyleProfile | None",
        "VitalitySnapshot | None",
        "list[DailyLog]",
    ]:
        """Load context directly from the database.

        Args:
            patient_id: The patient to load context for.

        Returns:
            Tuple of ``(lifestyle, snapshot, daily_logs)``.
        """
        from sqlalchemy import select

        from app.models.daily_log import DailyLog as DailyLogModel
        from app.models.lifestyle_profile import LifestyleProfile as LifestyleProfileModel
        from app.models.vitality_snapshot import VitalitySnapshot as VitalitySnapshotModel

        session = self._session
        assert session is not None

        # LifestyleProfile (one row per patient, PK is patient_id)
        lp_pid = getattr(LifestyleProfileModel, "patient_id")
        lp_stmt = select(LifestyleProfileModel).where(lp_pid == patient_id)
        lp_result = await session.execute(lp_stmt)
        lifestyle = lp_result.scalars().first()

        # VitalitySnapshot (one row per patient, PK is patient_id)
        vs_pid = getattr(VitalitySnapshotModel, "patient_id")
        vs_stmt = select(VitalitySnapshotModel).where(vs_pid == patient_id)
        vs_result = await session.execute(vs_stmt)
        snapshot = vs_result.scalars().first()

        # DailyLog — last 7 days
        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        week_ago = now - datetime.timedelta(days=_LOG_LOOKBACK_DAYS)

        dl_pid = getattr(DailyLogModel, "patient_id")
        dl_logged_at = getattr(DailyLogModel, "logged_at")
        dl_stmt = (
            select(DailyLogModel)
            .where(dl_pid == patient_id)
            .where(dl_logged_at >= week_ago)
            .where(dl_logged_at <= now)
            .order_by(dl_logged_at.desc())
        )
        dl_result = await session.execute(dl_stmt)
        daily_logs = list(dl_result.scalars().all())

        return lifestyle, snapshot, daily_logs
