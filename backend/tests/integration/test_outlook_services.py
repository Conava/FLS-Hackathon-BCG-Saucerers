"""Integration tests for OutlookNarratorService and FutureSelfService.

Uses:
  - ``FakeLLMProvider`` — deterministic, no network.
  - ``db_session`` fixture — real Postgres via Testcontainers, per-test rollback.

Scenarios:
  1. OutlookNarratorService.narrate() returns one sentence + disclaimer + ai_meta.
  2. OutlookNarratorService.narrate() persists the VitalityOutlook row via the repo.
  3. Calling narrate() twice for the same patient + horizon upserts, not duplicates.
  4. FutureSelfService.project() returns bio_age + narrative + disclaimer + ai_meta.
  5. Cross-patient isolation: narrate for PT_A does not affect PT_B.
"""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 — registers all SQLModel tables


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _dt() -> datetime.datetime:
    """Return a naive UTC datetime."""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


def _make_patient(patient_id: str) -> "app.models.Patient":  # type: ignore[name-defined]
    return app.models.Patient(  # type: ignore[attr-defined]
        patient_id=patient_id,
        name=f"Test {patient_id}",
        age=40,
        sex="unknown",
        country="DE",
        created_at=_dt(),
        updated_at=_dt(),
    )


def _make_outlook(patient_id: str, horizon_months: int = 3) -> "app.models.VitalityOutlook":  # type: ignore[name-defined]
    return app.models.VitalityOutlook(  # type: ignore[attr-defined]
        patient_id=patient_id,
        horizon_months=horizon_months,
        projected_score=72.0,
        narrative="Placeholder narrative",
        computed_at=_dt(),
    )


# ---------------------------------------------------------------------------
# OutlookNarratorService
# ---------------------------------------------------------------------------


class TestOutlookNarratorService:
    """End-to-end tests for OutlookNarratorService using FakeLLMProvider."""

    async def test_narrate_returns_response_with_narrative(
        self, db_session: AsyncSession
    ) -> None:
        """narrate() returns an OutlookNarratorResponse with a non-empty narrative."""
        from app.ai.llm import FakeLLMProvider
        from app.services.outlook_narrator import OutlookNarratorService

        db_session.add(_make_patient("PT_NAR001"))
        await db_session.flush()

        outlook = _make_outlook("PT_NAR001", horizon_months=3)
        db_session.add(outlook)
        await db_session.flush()

        service = OutlookNarratorService(llm=FakeLLMProvider(), session=db_session)
        response = await service.narrate(patient_id="PT_NAR001", outlook=outlook)

        assert response.narrative, "narrative must be a non-empty string"

    async def test_narrate_returns_disclaimer(self, db_session: AsyncSession) -> None:
        """narrate() response includes the wellness disclaimer."""
        from app.ai.llm import FakeLLMProvider
        from app.services.outlook_narrator import OutlookNarratorService

        db_session.add(_make_patient("PT_NAR002"))
        await db_session.flush()

        outlook = _make_outlook("PT_NAR002", horizon_months=6)
        db_session.add(outlook)
        await db_session.flush()

        service = OutlookNarratorService(llm=FakeLLMProvider(), session=db_session)
        response = await service.narrate(patient_id="PT_NAR002", outlook=outlook)

        assert response.disclaimer, "disclaimer field must be present and non-empty"
        # Wellness framing: no diagnostic verbs
        for forbidden in ("diagnose", "treat", "cure", "prevent-disease"):
            assert forbidden.lower() not in response.disclaimer.lower(), (
                f"Forbidden word '{forbidden}' found in disclaimer"
            )

    async def test_narrate_returns_ai_meta(self, db_session: AsyncSession) -> None:
        """narrate() response includes ai_meta with prompt_name, model, request_id."""
        from app.ai.llm import FakeLLMProvider
        from app.services.outlook_narrator import OutlookNarratorService

        db_session.add(_make_patient("PT_NAR003"))
        await db_session.flush()

        outlook = _make_outlook("PT_NAR003", horizon_months=3)
        db_session.add(outlook)
        await db_session.flush()

        service = OutlookNarratorService(llm=FakeLLMProvider(), session=db_session)
        response = await service.narrate(patient_id="PT_NAR003", outlook=outlook)

        assert response.ai_meta is not None
        assert response.ai_meta.prompt_name == "outlook-narrator"
        assert response.ai_meta.model, "model must be non-empty"
        assert response.ai_meta.request_id, "request_id must be non-empty"
        # Token counts are set (may be 0 for FakeLLMProvider)
        assert response.ai_meta.token_in >= 0
        assert response.ai_meta.token_out >= 0
        assert response.ai_meta.latency_ms >= 0

    async def test_narrate_persists_outlook_via_repo(
        self, db_session: AsyncSession
    ) -> None:
        """narrate() upserts the VitalityOutlook row with updated narrative."""
        from sqlalchemy import select

        from app.ai.llm import FakeLLMProvider
        from app.models.vitality_outlook import VitalityOutlook
        from app.services.outlook_narrator import OutlookNarratorService

        db_session.add(_make_patient("PT_NAR004"))
        await db_session.flush()

        outlook = _make_outlook("PT_NAR004", horizon_months=3)
        db_session.add(outlook)
        await db_session.flush()
        original_id = outlook.id

        service = OutlookNarratorService(llm=FakeLLMProvider(), session=db_session)
        response = await service.narrate(patient_id="PT_NAR004", outlook=outlook)

        # Verify the row in DB reflects the narrator's narrative
        stmt = (
            select(VitalityOutlook)
            .where(getattr(VitalityOutlook, "patient_id") == "PT_NAR004")
            .where(getattr(VitalityOutlook, "horizon_months") == 3)
        )
        result = await db_session.execute(stmt)
        rows = list(result.scalars().all())
        assert len(rows) >= 1

        # The narrative from the response should be stored
        narratives = [r.narrative for r in rows]
        assert response.narrative in narratives, (
            f"Expected narrative '{response.narrative}' in stored narratives {narratives}"
        )

    async def test_narrate_upserts_not_duplicates(
        self, db_session: AsyncSession
    ) -> None:
        """Calling narrate() twice for the same patient+horizon updates, not duplicates."""
        from sqlalchemy import select

        from app.ai.llm import FakeLLMProvider
        from app.models.vitality_outlook import VitalityOutlook
        from app.services.outlook_narrator import OutlookNarratorService

        db_session.add(_make_patient("PT_NAR005"))
        await db_session.flush()

        outlook = _make_outlook("PT_NAR005", horizon_months=6)
        db_session.add(outlook)
        await db_session.flush()

        service = OutlookNarratorService(llm=FakeLLMProvider(), session=db_session)
        await service.narrate(patient_id="PT_NAR005", outlook=outlook)
        await service.narrate(patient_id="PT_NAR005", outlook=outlook)

        stmt = (
            select(VitalityOutlook)
            .where(getattr(VitalityOutlook, "patient_id") == "PT_NAR005")
            .where(getattr(VitalityOutlook, "horizon_months") == 6)
        )
        result = await db_session.execute(stmt)
        rows = list(result.scalars().all())
        # Should have at most one row per (patient_id, horizon_months)
        assert len(rows) == 1, (
            f"Expected 1 row after upsert, got {len(rows)}"
        )


# ---------------------------------------------------------------------------
# Cross-patient isolation for OutlookNarratorService
# ---------------------------------------------------------------------------


class TestOutlookNarratorIsolation:
    """Narrating for PT_A must not affect or expose PT_B data."""

    async def test_narrate_isolation(self, db_session: AsyncSession) -> None:
        """Narratating for PT_A does not create rows for PT_B."""
        from sqlalchemy import select

        from app.ai.llm import FakeLLMProvider
        from app.models.vitality_outlook import VitalityOutlook
        from app.services.outlook_narrator import OutlookNarratorService

        db_session.add(_make_patient("PT_ISO_A"))
        db_session.add(_make_patient("PT_ISO_B"))
        await db_session.flush()

        outlook_a = _make_outlook("PT_ISO_A", horizon_months=3)
        db_session.add(outlook_a)
        await db_session.flush()

        service = OutlookNarratorService(llm=FakeLLMProvider(), session=db_session)
        await service.narrate(patient_id="PT_ISO_A", outlook=outlook_a)

        # PT_ISO_B should have no outlook rows
        stmt = select(VitalityOutlook).where(
            getattr(VitalityOutlook, "patient_id") == "PT_ISO_B"
        )
        result = await db_session.execute(stmt)
        rows = list(result.scalars().all())
        assert len(rows) == 0, f"Expected 0 rows for PT_ISO_B, got {len(rows)}"


# ---------------------------------------------------------------------------
# FutureSelfService
# ---------------------------------------------------------------------------


class TestFutureSelfService:
    """End-to-end tests for FutureSelfService using FakeLLMProvider."""

    async def test_project_returns_bio_age(self, db_session: AsyncSession) -> None:
        """project() returns a FutureSelfResponse with a non-negative bio_age."""
        from app.ai.llm import FakeLLMProvider
        from app.services.future_self import FutureSelfService

        db_session.add(_make_patient("PT_FS001"))
        await db_session.flush()

        service = FutureSelfService(llm=FakeLLMProvider(), session=db_session)
        response = await service.project(
            patient_id="PT_FS001",
            sliders={"sleep_improvement": 2, "exercise_frequency": 4},
        )

        assert isinstance(response.bio_age, int), "bio_age must be an int"
        assert response.bio_age >= 0, "bio_age must be non-negative"

    async def test_project_returns_narrative(self, db_session: AsyncSession) -> None:
        """project() returns a non-empty narrative string."""
        from app.ai.llm import FakeLLMProvider
        from app.services.future_self import FutureSelfService

        db_session.add(_make_patient("PT_FS002"))
        await db_session.flush()

        service = FutureSelfService(llm=FakeLLMProvider(), session=db_session)
        response = await service.project(
            patient_id="PT_FS002",
            sliders={"nutrition": 3},
        )

        assert response.narrative, "narrative must be a non-empty string"

    async def test_project_returns_disclaimer(self, db_session: AsyncSession) -> None:
        """project() response includes the wellness disclaimer, no diagnostic verbs."""
        from app.ai.llm import FakeLLMProvider
        from app.services.future_self import FutureSelfService

        db_session.add(_make_patient("PT_FS003"))
        await db_session.flush()

        service = FutureSelfService(llm=FakeLLMProvider(), session=db_session)
        response = await service.project(
            patient_id="PT_FS003",
            sliders={},
        )

        assert response.disclaimer, "disclaimer must be present and non-empty"
        for forbidden in ("diagnose", "treat", "cure", "prevent-disease"):
            assert forbidden.lower() not in response.disclaimer.lower(), (
                f"Forbidden word '{forbidden}' found in disclaimer"
            )

    async def test_project_returns_ai_meta(self, db_session: AsyncSession) -> None:
        """project() response includes ai_meta with correct prompt_name."""
        from app.ai.llm import FakeLLMProvider
        from app.services.future_self import FutureSelfService

        db_session.add(_make_patient("PT_FS004"))
        await db_session.flush()

        service = FutureSelfService(llm=FakeLLMProvider(), session=db_session)
        response = await service.project(
            patient_id="PT_FS004",
            sliders={"sleep_improvement": 1},
        )

        assert response.ai_meta is not None
        assert response.ai_meta.prompt_name == "future-self"
        assert response.ai_meta.model, "model must be non-empty"
        assert response.ai_meta.request_id, "request_id must be non-empty"

    async def test_project_with_empty_sliders(self, db_session: AsyncSession) -> None:
        """project() works with an empty sliders dict — graceful no-op."""
        from app.ai.llm import FakeLLMProvider
        from app.services.future_self import FutureSelfService

        db_session.add(_make_patient("PT_FS005"))
        await db_session.flush()

        service = FutureSelfService(llm=FakeLLMProvider(), session=db_session)
        response = await service.project(
            patient_id="PT_FS005",
            sliders={},
        )

        # Must not raise; response must be structurally valid
        assert response.bio_age >= 0
        assert response.narrative
        assert response.disclaimer
        assert response.ai_meta is not None
