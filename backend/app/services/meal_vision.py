"""MealVisionService — upload, analyse, and persist a meal photo.

Pipeline
--------
1. Fetch the patient's ``LifestyleProfile`` to extract dietary context.
2. Store the image via ``PhotoStorage.put`` → returns a URI.
3. Load the ``meal-vision`` system prompt.
4. Call ``LLMProvider.generate_vision`` with the prompt, image bytes, and
   ``MealAnalysis`` response schema.
5. Validate the LLM result via ``MealAnalysis.model_validate``.
6. Persist a ``MealLog`` row with the photo URI, macros, swap suggestion, and
   ``analyzed_at`` timestamp via ``MealLogRepository``.
7. Return ``(MealLog, MealAnalysis)`` to the caller.

GDPR / PHI policy
-----------------
No patient name, date of birth, or other PHI is logged — only request metadata
(patient_id, model, prompt_name, photo_uri prefix).

Stack: FastAPI + SQLModel + SQLAlchemy 2.0 async + google-genai LLM provider.
"""
from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompt_loader import load_prompt
from app.core.logging import get_logger
from app.models.lifestyle_profile import LifestyleProfile
from app.models.meal_log import MealLog
from app.repositories.meal_log_repo import MealLogRepository
from app.schemas.meal_log import MealAnalysis

if TYPE_CHECKING:
    from app.adapters.photo_storage import PhotoStorage
    from app.ai.llm import LLMProvider

_logger: logging.Logger = get_logger(__name__)

_PROMPT_NAME = "meal-vision.system"
_VISION_MODEL = "gemini-2.5-flash"


def _utcnow() -> datetime.datetime:
    """Return current UTC time as timezone-naive datetime (CLAUDE.md lesson)."""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


def _build_dietary_context(profile: LifestyleProfile | None) -> str:
    """Build a diet-context string from the patient's LifestyleProfile.

    ``LifestyleProfile`` does not have a ``dietary_restrictions`` free-text
    field — it captures numeric lifestyle metrics instead.  This helper
    assembles a concise context sentence from the available fields so the
    meal-vision model can tailor swap suggestions appropriately.

    Args:
        profile: The patient's ``LifestyleProfile``, or ``None`` if not present.

    Returns:
        A short, wellness-framed context string, e.g.
        ``"Diet quality score: 9/10. Non-smoker. Alcohol: 2 units/week."``
        Returns ``"No dietary restrictions on file."`` when profile is absent.
    """
    if profile is None:
        return "No dietary restrictions on file."

    parts: list[str] = []

    if profile.diet_quality_score is not None:
        parts.append(f"Diet quality score: {profile.diet_quality_score}/10")

    if profile.smoking_status is not None:
        parts.append(f"Smoking status: {profile.smoking_status}")

    if profile.alcohol_units_weekly is not None:
        parts.append(f"Alcohol: {profile.alcohol_units_weekly} units/week")

    if profile.fruit_veg_servings_daily is not None:
        parts.append(f"Fruit/veg servings daily: {profile.fruit_veg_servings_daily}")

    if not parts:
        return "No specific dietary data on file."

    return ". ".join(parts) + "."


class MealVisionService:
    """Orchestrates meal-photo upload, Gemini Vision analysis, and persistence.

    Parameters
    ----------
    session:
        Open ``AsyncSession`` owned by the caller (FastAPI request or test
        fixture).  This service does not commit — the caller controls the
        transaction boundary.
    photo_storage:
        A ``PhotoStorage`` adapter (``LocalFsPhotoStorage`` in dev/tests,
        ``GcsPhotoStorage`` in production).
    llm:
        An ``LLMProvider`` (``FakeLLMProvider`` in tests,
        ``GeminiProvider`` in production).
    """

    def __init__(
        self,
        session: AsyncSession,
        photo_storage: PhotoStorage,
        llm: LLMProvider,
    ) -> None:
        self._session = session
        self._storage = photo_storage
        self._llm = llm
        self._repo = MealLogRepository(session)

    async def analyze_and_log(
        self,
        patient_id: str,
        image_bytes: bytes,
        filename: str,
        notes: str | None = None,
    ) -> tuple[MealLog, MealAnalysis]:
        """Upload, analyse, and persist a meal photo for a patient.

        Steps:
        1. Fetch ``LifestyleProfile`` for dietary context.
        2. Store the image via ``PhotoStorage.put``.
        3. Load the ``meal-vision`` system prompt.
        4. Call ``LLMProvider.generate_vision`` with the ``MealAnalysis`` schema.
        5. Validate result via ``MealAnalysis.model_validate``.
        6. Persist ``MealLog`` with photo URI, macros, swap suggestion, and
           ``analyzed_at = datetime.now(UTC).replace(tzinfo=None)``.
        7. Return ``(MealLog, MealAnalysis)``.

        Args:
            patient_id:   Patient the meal belongs to.
            image_bytes:  Raw image bytes (JPEG or PNG).
            filename:     Original filename — extension is preserved for storage.
            notes:        Optional free-text notes from the patient (passed to LLM).

        Returns:
            A tuple of ``(MealLog, MealAnalysis)``.  ``MealLog.id`` is populated
            (``flush`` has been called by the repository).

        Raises:
            pydantic.ValidationError: If the LLM response does not conform to
                ``MealAnalysis``.
        """
        # ------------------------------------------------------------------
        # 1. Fetch LifestyleProfile for dietary context
        # ------------------------------------------------------------------
        pid_attr = LifestyleProfile.patient_id
        stmt = select(LifestyleProfile).where(pid_attr == patient_id)
        result = await self._session.execute(stmt)
        profile: LifestyleProfile | None = result.scalars().first()

        dietary_context = _build_dietary_context(profile)

        # ------------------------------------------------------------------
        # 2. Store the image
        # ------------------------------------------------------------------
        photo_uri = self._storage.put(patient_id, filename, image_bytes)

        _logger.info(
            "meal_photo_stored",
            extra={
                "patient_id": patient_id,
                "photo_uri_prefix": photo_uri[:30],  # no full path in logs
            },
        )

        # ------------------------------------------------------------------
        # 3. Load system prompt
        # ------------------------------------------------------------------
        system_prompt = load_prompt(_PROMPT_NAME)

        # ------------------------------------------------------------------
        # 4. Call LLM vision
        # ------------------------------------------------------------------
        user_prompt_parts = [f"Dietary context: {dietary_context}"]
        if notes:
            user_prompt_parts.append(f"Patient notes: {notes}")
        user_prompt = "\n".join(user_prompt_parts)

        raw_result = await self._llm.generate_vision(
            system=system_prompt,
            prompt=user_prompt,
            image_bytes=image_bytes,
            model=_VISION_MODEL,
            response_schema=MealAnalysis,
        )

        # ------------------------------------------------------------------
        # 5. Validate result
        # ------------------------------------------------------------------
        analysis = MealAnalysis.model_validate(raw_result)

        _logger.info(
            "meal_vision_analyzed",
            extra={
                "patient_id": patient_id,
                "model": _VISION_MODEL,
                "prompt_name": _PROMPT_NAME,
            },
        )

        # ------------------------------------------------------------------
        # 6. Persist MealLog
        # ------------------------------------------------------------------
        # Store full analysis (classification, macros, swap_rationale) in the
        # JSONB macros column.  longevity_swap gets its own text column for
        # easy querying.  analyzed_at must be naive UTC (CLAUDE.md lesson).
        macros_payload: dict = {
            "classification": analysis.classification,
            "kcal": analysis.macros.get("kcal"),
            "protein_g": analysis.macros.get("protein_g"),
            "carbs_g": analysis.macros.get("carbs_g"),
            "fat_g": analysis.macros.get("fat_g"),
            "fiber_g": analysis.macros.get("fiber_g"),
            "swap_rationale": analysis.swap_rationale,
        }

        meal_log = MealLog(
            patient_id=patient_id,
            photo_uri=photo_uri,
            macros=macros_payload,
            longevity_swap=analysis.longevity_swap,
            analyzed_at=_utcnow(),
        )
        persisted = await self._repo.create(patient_id=patient_id, meal=meal_log)

        return persisted, analysis
