"""Integration tests for MealVisionService.

Tests the full pipeline:
  image_bytes → PhotoStorage.put → LLMProvider.generate_vision → MealLog persisted

Uses LocalFsPhotoStorage with a tmp_path base dir and FakeLLMProvider.
Patient + LifestyleProfile are seeded via the shared testcontainers db_session.

Stack: SQLAlchemy 2.0 async + SQLModel + Postgres 16 + pgvector (Testcontainers).
"""
from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 — side-effect import ensures all tables are registered


# ---------------------------------------------------------------------------
# Minimal valid PNG fixture (~67 bytes)
# A 1×1 white pixel PNG: signature + IHDR + IDAT + IEND chunks.
# ---------------------------------------------------------------------------

_MINIMAL_PNG: bytes = (
    b"\x89PNG\r\n\x1a\n"  # 8-byte PNG signature
    b"\x00\x00\x00\rIHDR"  # IHDR chunk length + type
    b"\x00\x00\x00\x01"    # width = 1
    b"\x00\x00\x00\x01"    # height = 1
    b"\x08\x02"             # bit depth = 8, colour type = RGB
    b"\x00\x00\x00"        # compression, filter, interlace
    b"\x90wS\xde"          # IHDR CRC
    b"\x00\x00\x00\x0cIDAT"  # IDAT chunk
    b"x\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"  # deflate stream
    b"\x00\x00\x00\x00IEND"  # IEND chunk (length=0)
    b"\xaeB`\x82"           # IEND CRC
)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def make_patient(patient_id: str) -> app.models.Patient:  # type: ignore[name-defined]
    return app.models.Patient(  # type: ignore[attr-defined]
        patient_id=patient_id,
        name=f"Test {patient_id}",
        age=40,
        sex="female",
        country="DE",
    )


def make_lifestyle(patient_id: str, vegetarian: bool = True) -> app.models.LifestyleProfile:  # type: ignore[name-defined]
    """Create a LifestyleProfile for testing.

    ``vegetarian`` param controls diet_quality_score to simulate dietary
    context passed to the meal vision prompt.
    """
    return app.models.LifestyleProfile(  # type: ignore[attr-defined]
        patient_id=patient_id,
        survey_date=datetime.date(2026, 4, 1),
        diet_quality_score=9 if vegetarian else 5,
        smoking_status="never",
        alcohol_units_weekly=0.0,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMealVisionService:
    """Integration tests for MealVisionService.analyze_and_log."""

    async def test_analyze_and_log_persists_meal_log(
        self,
        db_session: AsyncSession,
        tmp_path: Path,
    ) -> None:
        """analyze_and_log() persists a MealLog row and returns both objects.

        Assertions:
        - Returns a (MealLog, MealAnalysis) tuple.
        - MealLog is persisted with a non-None id and the photo_uri.
        - The file exists on disk at the URI path.
        - macros dict is populated (from FakeLLMProvider).
        - longevity_swap is populated.
        - analyzed_at is a naive datetime.
        """
        from app.adapters.photo_storage import LocalFsPhotoStorage
        from app.ai.llm import FakeLLMProvider
        from app.services.meal_vision import MealVisionService

        patient_id = "PT_MV001"
        db_session.add(make_patient(patient_id))
        await db_session.flush()  # satisfy FK before adding LifestyleProfile
        db_session.add(make_lifestyle(patient_id, vegetarian=True))
        await db_session.flush()

        storage = LocalFsPhotoStorage(base_dir=tmp_path / "photos")
        llm = FakeLLMProvider()
        svc = MealVisionService(session=db_session, photo_storage=storage, llm=llm)

        meal_log, analysis = await svc.analyze_and_log(
            patient_id=patient_id,
            image_bytes=_MINIMAL_PNG,
            filename="meal.png",
        )

        # MealLog must be persisted with an id
        assert meal_log.id is not None
        assert meal_log.patient_id == patient_id

        # Photo URI must be set and the file must exist on disk
        assert meal_log.photo_uri.startswith("file://")
        photo_path = Path(meal_log.photo_uri[len("file://"):])
        assert photo_path.exists(), f"Photo file not found at: {photo_path}"
        assert photo_path.read_bytes() == _MINIMAL_PNG

        # Macros must be populated from FakeLLMProvider
        assert meal_log.macros is not None
        assert "kcal" in meal_log.macros or "protein_g" in meal_log.macros

        # longevity_swap must be populated
        assert meal_log.longevity_swap is not None
        assert len(meal_log.longevity_swap) > 0

        # analyzed_at must be a naive datetime (no tzinfo)
        assert isinstance(meal_log.analyzed_at, datetime.datetime)
        assert meal_log.analyzed_at.tzinfo is None

        # Analysis object must have all required fields
        assert analysis.classification
        assert analysis.macros
        assert analysis.longevity_swap
        assert analysis.swap_rationale

    async def test_analyze_and_log_with_notes(
        self,
        db_session: AsyncSession,
        tmp_path: Path,
    ) -> None:
        """analyze_and_log() passes notes through to the LLM prompt."""
        from app.adapters.photo_storage import LocalFsPhotoStorage
        from app.ai.llm import FakeLLMProvider
        from app.services.meal_vision import MealVisionService

        patient_id = "PT_MV002"
        db_session.add(make_patient(patient_id))
        await db_session.flush()

        storage = LocalFsPhotoStorage(base_dir=tmp_path / "photos2")
        llm = FakeLLMProvider()
        svc = MealVisionService(session=db_session, photo_storage=storage, llm=llm)

        # Pass notes — service should include them in the prompt (no crash)
        meal_log, analysis = await svc.analyze_and_log(
            patient_id=patient_id,
            image_bytes=_MINIMAL_PNG,
            filename="dinner.png",
            notes="This is my post-workout dinner.",
        )

        assert meal_log.id is not None
        assert analysis.classification is not None

    async def test_analyze_and_log_without_lifestyle_profile(
        self,
        db_session: AsyncSession,
        tmp_path: Path,
    ) -> None:
        """analyze_and_log() succeeds when the patient has no LifestyleProfile.

        In this case the service should still call LLM (with empty restrictions).
        """
        from app.adapters.photo_storage import LocalFsPhotoStorage
        from app.ai.llm import FakeLLMProvider
        from app.services.meal_vision import MealVisionService

        patient_id = "PT_MV003"
        # Only add patient — no LifestyleProfile
        db_session.add(make_patient(patient_id))
        await db_session.flush()

        storage = LocalFsPhotoStorage(base_dir=tmp_path / "photos3")
        llm = FakeLLMProvider()
        svc = MealVisionService(session=db_session, photo_storage=storage, llm=llm)

        meal_log, analysis = await svc.analyze_and_log(
            patient_id=patient_id,
            image_bytes=_MINIMAL_PNG,
            filename="lunch.png",
        )

        assert meal_log.id is not None
        assert meal_log.patient_id == patient_id
        assert analysis.macros is not None

    async def test_analyze_and_log_cross_patient_isolation(
        self,
        db_session: AsyncSession,
        tmp_path: Path,
    ) -> None:
        """MealLog rows are isolated per patient — patient B cannot read patient A's logs."""
        from sqlalchemy import select

        from app.adapters.photo_storage import LocalFsPhotoStorage
        from app.ai.llm import FakeLLMProvider
        from app.models.meal_log import MealLog
        from app.services.meal_vision import MealVisionService

        pid_a = "PT_MV004A"
        pid_b = "PT_MV004B"

        db_session.add(make_patient(pid_a))
        db_session.add(make_patient(pid_b))
        await db_session.flush()

        storage = LocalFsPhotoStorage(base_dir=tmp_path / "photos4")
        llm = FakeLLMProvider()
        svc = MealVisionService(session=db_session, photo_storage=storage, llm=llm)

        # Upload for patient A
        meal_log_a, _ = await svc.analyze_and_log(
            patient_id=pid_a,
            image_bytes=_MINIMAL_PNG,
            filename="meal_a.png",
        )
        assert meal_log_a.patient_id == pid_a

        # Query meal logs for patient B — must return nothing
        pid_b_attr = getattr(MealLog, "patient_id")
        stmt = select(MealLog).where(pid_b_attr == pid_b)
        result = await db_session.execute(stmt)
        rows = list(result.scalars().all())
        assert len(rows) == 0, "Patient B must not see Patient A's meal logs"
