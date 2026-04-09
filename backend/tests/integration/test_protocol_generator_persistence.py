"""Integration tests for ProtocolGeneratorService persistence.

Seeds a real patient + LifestyleProfile + VitalitySnapshot via testcontainers
Postgres, runs the generator with FakeLLMProvider, and asserts that Protocol
+ ProtocolAction rows land in the database.

Uses the ``db_session`` fixture from tests/conftest.py (per-test rollback).
"""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 — registers all SQLModel tables

from app.ai.llm import FakeLLMProvider
from app.models.daily_log import DailyLog
from app.models.lifestyle_profile import LifestyleProfile
from app.models.patient import Patient
from app.models.protocol import Protocol, ProtocolAction
from app.models.vitality_snapshot import VitalitySnapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_patient(patient_id: str = "PT_PG001") -> Patient:
    return Patient(
        patient_id=patient_id,
        name=f"Test {patient_id}",
        age=42,
        sex="female",
        country="DE",
    )


def _make_lifestyle(
    patient_id: str = "PT_PG001",
    time_budget: int = 60,
) -> LifestyleProfile:
    return LifestyleProfile(
        patient_id=patient_id,
        survey_date=datetime.date(2026, 4, 7),
        diet_quality_score=7,
        time_budget_minutes_per_day=time_budget,
    )


def _make_snapshot(patient_id: str = "PT_PG001") -> VitalitySnapshot:
    return VitalitySnapshot(
        patient_id=patient_id,
        computed_at=datetime.datetime(2026, 4, 8, 10, 0, 0),
        score=72.5,
        subscores={"cardio": 70, "metabolic": 75, "sleep": 68, "activity": 80, "lifestyle": 65},
        risk_flags={},
    )


def _make_generated_protocol(num_actions: int = 3, minutes_per_action: int = 15) -> dict:
    """Return a valid GeneratedProtocol-shaped dict."""
    actions = []
    for i in range(num_actions):
        actions.append({
            "category": "movement",
            "title": f"Action {i + 1}",
            "target": f"{minutes_per_action} min",
            "rationale": f"Rationale {i + 1}",
            "dimension": "cardio_fitness",
        })
    return {
        "rationale": "Weekly protocol for movement focus.",
        "actions": actions,
    }


async def _seed_patient(
    db_session: AsyncSession,
    patient_id: str,
    time_budget: int = 60,
    with_snapshot: bool = True,
) -> None:
    """Seed patient + lifestyle profile + optional snapshot, flushing after each FK."""
    patient = _make_patient(patient_id)
    db_session.add(patient)
    await db_session.flush()  # patient must exist before child rows

    lifestyle = _make_lifestyle(patient_id, time_budget=time_budget)
    db_session.add(lifestyle)
    await db_session.flush()

    if with_snapshot:
        snapshot = _make_snapshot(patient_id)
        db_session.add(snapshot)
        await db_session.flush()


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.integration
class TestProtocolGeneratorPersistence:
    """Integration tests: seed DB, run service, verify rows written."""

    async def test_generate_creates_protocol_and_actions(
        self, db_session: AsyncSession
    ) -> None:
        """generate_for_patient persists Protocol + 3 ProtocolAction rows in DB."""
        await _seed_patient(db_session, "PT_PG001", time_budget=60)

        fake_llm = FakeLLMProvider()
        generated = _make_generated_protocol(num_actions=3, minutes_per_action=15)
        fake_llm.generate = AsyncMock(return_value=generated)  # type: ignore[method-assign]

        from app.repositories.protocol_repo import (
            ProtocolActionRepository,
            ProtocolRepository,
        )
        from app.services.protocol_generator import ProtocolGeneratorService

        protocol_repo = ProtocolRepository(db_session)
        action_repo = ProtocolActionRepository(db_session)

        svc = ProtocolGeneratorService(
            llm_provider=fake_llm,
            protocol_repo=protocol_repo,
            action_repo=action_repo,
            session=db_session,
        )

        result = await svc.generate_for_patient("PT_PG001")

        # Protocol row
        assert result.id is not None
        assert result.patient_id == "PT_PG001"

        # Actions in DB
        actions = await action_repo.list_for_patient(patient_id="PT_PG001")
        assert len(actions) == 3
        assert all(a.protocol_id == result.id for a in actions)

    async def test_generate_uses_lifestyle_time_budget(
        self, db_session: AsyncSession
    ) -> None:
        """Service reads time_budget from LifestyleProfile; too-long actions raise."""
        await _seed_patient(db_session, "PT_PG002", time_budget=30)

        fake_llm = FakeLLMProvider()
        # 4 actions × 10 min = 40 min > 30 budget → ValueError
        generated = _make_generated_protocol(num_actions=4, minutes_per_action=10)
        fake_llm.generate = AsyncMock(return_value=generated)  # type: ignore[method-assign]

        from app.repositories.protocol_repo import (
            ProtocolActionRepository,
            ProtocolRepository,
        )
        from app.services.protocol_generator import ProtocolGeneratorService

        svc = ProtocolGeneratorService(
            llm_provider=fake_llm,
            protocol_repo=ProtocolRepository(db_session),
            action_repo=ProtocolActionRepository(db_session),
            session=db_session,
        )

        with pytest.raises(ValueError, match="time_budget"):
            await svc.generate_for_patient("PT_PG002")

    async def test_generate_with_daily_logs_adheres_to_context(
        self, db_session: AsyncSession
    ) -> None:
        """Service reads last-7-day DailyLogs for adherence context."""
        await _seed_patient(db_session, "PT_PG003", time_budget=60)

        # Add some daily logs (last 7 days)
        base_dt = datetime.datetime(2026, 4, 9, 8, 0, 0)
        for delta in range(5):
            log = DailyLog(
                patient_id="PT_PG003",
                logged_at=base_dt - datetime.timedelta(days=delta),
                mood=4,
                workout_minutes=30,
                sleep_hours=7.5,
            )
            db_session.add(log)
        await db_session.flush()

        fake_llm = FakeLLMProvider()
        generated = _make_generated_protocol(num_actions=3, minutes_per_action=15)
        fake_llm.generate = AsyncMock(return_value=generated)  # type: ignore[method-assign]

        from app.repositories.protocol_repo import (
            ProtocolActionRepository,
            ProtocolRepository,
        )
        from app.services.protocol_generator import ProtocolGeneratorService

        svc = ProtocolGeneratorService(
            llm_provider=fake_llm,
            protocol_repo=ProtocolRepository(db_session),
            action_repo=ProtocolActionRepository(db_session),
            session=db_session,
        )

        result = await svc.generate_for_patient("PT_PG003")
        assert result is not None

        # Verify the LLM was called (once) — context was assembled
        fake_llm.generate.assert_called_once()  # type: ignore[attr-defined]
        # Verify adherence summary was included in the user context
        call_kwargs = fake_llm.generate.call_args.kwargs  # type: ignore[attr-defined]
        assert "adherence" in call_kwargs["user"].lower() or "log" in call_kwargs["user"].lower()

    async def test_protocol_row_has_correct_status(
        self, db_session: AsyncSession
    ) -> None:
        """Generated Protocol row has status='active'."""
        await _seed_patient(db_session, "PT_PG004", time_budget=60, with_snapshot=False)

        fake_llm = FakeLLMProvider()
        fake_llm.generate = AsyncMock(return_value=_make_generated_protocol())  # type: ignore[method-assign]

        from app.repositories.protocol_repo import (
            ProtocolActionRepository,
            ProtocolRepository,
        )
        from app.services.protocol_generator import ProtocolGeneratorService

        svc = ProtocolGeneratorService(
            llm_provider=fake_llm,
            protocol_repo=ProtocolRepository(db_session),
            action_repo=ProtocolActionRepository(db_session),
            session=db_session,
        )

        result = await svc.generate_for_patient("PT_PG004")
        assert result.status == "active"
