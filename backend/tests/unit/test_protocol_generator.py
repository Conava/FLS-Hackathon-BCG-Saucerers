"""Unit tests for ProtocolGeneratorService.

Tests use FakeLLMProvider with monkeypatched ``generate`` to control the
returned GeneratedProtocol dict precisely.  No DB — repositories are stubbed
with in-memory fakes.

Covers:
  - Valid protocol → persisted with correct action count
  - >7 actions → ValueError
  - Time budget exceeded → ValueError
  - Empty actions → ValueError
"""

from __future__ import annotations

import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.llm import FakeLLMProvider
from app.models.daily_log import DailyLog
from app.models.lifestyle_profile import LifestyleProfile
from app.models.protocol import Protocol, ProtocolAction
from app.models.vitality_snapshot import VitalitySnapshot


# ---------------------------------------------------------------------------
# Helpers — build test fixtures
# ---------------------------------------------------------------------------


def _make_lifestyle(
    patient_id: str = "PT_TEST",
    time_budget: int = 60,
) -> LifestyleProfile:
    """Return a minimal LifestyleProfile for testing."""
    return LifestyleProfile(
        patient_id=patient_id,
        survey_date=datetime.date(2026, 4, 7),
        diet_quality_score=7,
        time_budget_minutes_per_day=time_budget,
    )


def _make_snapshot(patient_id: str = "PT_TEST") -> VitalitySnapshot:
    """Return a minimal VitalitySnapshot for testing."""
    return VitalitySnapshot(
        patient_id=patient_id,
        computed_at=datetime.datetime(2026, 4, 8, 10, 0, 0),
        score=72.5,
        subscores={"cardio": 70, "metabolic": 75, "sleep": 68, "activity": 80, "lifestyle": 65},
        risk_flags={},
    )


def _make_generated_protocol(num_actions: int = 3, minutes_per_action: int = 15) -> dict:
    """Return a dict matching GeneratedProtocol schema shape."""
    actions = []
    for i in range(num_actions):
        actions.append({
            "category": "movement",
            "title": f"Action {i + 1}",
            "target": f"{minutes_per_action} min",
            "rationale": f"Rationale {i + 1}",
            "dimension": "cardio_fitness",
            "estimated_minutes": minutes_per_action,
        })
    return {
        "rationale": "Weekly wellness focus on movement and sleep.",
        "actions": actions,
    }


# ---------------------------------------------------------------------------
# Fake repositories — in-memory stubs
# ---------------------------------------------------------------------------


class FakeProtocolRepository:
    """In-memory stub for ProtocolRepository."""

    def __init__(self) -> None:
        self.created: list[Protocol] = []
        self._next_id = 1

    async def create(self, *, patient_id: str, protocol: Protocol) -> Protocol:
        object.__setattr__(protocol, "patient_id", patient_id)
        object.__setattr__(protocol, "id", self._next_id)
        self._next_id += 1
        self.created.append(protocol)
        return protocol


class FakeProtocolActionRepository:
    """In-memory stub for ProtocolActionRepository."""

    def __init__(self) -> None:
        self.added: list[ProtocolAction] = []
        self._next_id = 1

    async def add(self, *, action: ProtocolAction) -> ProtocolAction:
        object.__setattr__(action, "id", self._next_id)
        self._next_id += 1
        self.added.append(action)
        return action


# ---------------------------------------------------------------------------
# Fake context builder — returns controlled lifestyle/snapshot/logs
# ---------------------------------------------------------------------------


class FakeContextProvider:
    """Provides controllable context data without a real DB."""

    def __init__(
        self,
        lifestyle: LifestyleProfile | None = None,
        snapshot: VitalitySnapshot | None = None,
        daily_logs: list[DailyLog] | None = None,
    ) -> None:
        self.lifestyle = lifestyle or _make_lifestyle()
        self.snapshot = snapshot
        self.daily_logs = daily_logs or []


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestProtocolGeneratorService:
    """Unit tests for ProtocolGeneratorService using fake dependencies."""

    async def _make_service(
        self,
        fake_llm: FakeLLMProvider,
        context: FakeContextProvider | None = None,
    ):
        """Create a ProtocolGeneratorService wired to fake dependencies."""
        from app.services.protocol_generator import ProtocolGeneratorService

        ctx = context or FakeContextProvider()
        protocol_repo = FakeProtocolRepository()
        action_repo = FakeProtocolActionRepository()

        svc = ProtocolGeneratorService(
            llm_provider=fake_llm,
            protocol_repo=protocol_repo,
            action_repo=action_repo,
        )
        # Inject the context provider so we don't need a real DB session
        svc._context_provider = ctx  # type: ignore[attr-defined]
        return svc, protocol_repo, action_repo

    async def test_valid_protocol_is_persisted(self) -> None:
        """A valid LLM response → Protocol + ProtocolAction rows created."""
        fake_llm = FakeLLMProvider()
        generated = _make_generated_protocol(num_actions=3, minutes_per_action=15)

        # Patch generate to return our controlled fixture
        fake_llm.generate = AsyncMock(return_value=generated)  # type: ignore[method-assign]

        ctx = FakeContextProvider(lifestyle=_make_lifestyle(time_budget=60))
        svc, proto_repo, action_repo = await self._make_service(fake_llm, ctx)

        result = await svc.generate_for_patient("PT_TEST")

        assert result is not None
        assert isinstance(result, Protocol)
        assert len(proto_repo.created) == 1
        assert len(action_repo.added) == 3

    async def test_valid_protocol_has_correct_action_count(self) -> None:
        """Actions in the repository match the generated count (5 actions)."""
        fake_llm = FakeLLMProvider()
        generated = _make_generated_protocol(num_actions=5, minutes_per_action=10)
        fake_llm.generate = AsyncMock(return_value=generated)  # type: ignore[method-assign]

        ctx = FakeContextProvider(lifestyle=_make_lifestyle(time_budget=60))
        svc, _, action_repo = await self._make_service(fake_llm, ctx)

        await svc.generate_for_patient("PT_TEST")
        assert len(action_repo.added) == 5

    async def test_more_than_7_actions_raises_value_error(self) -> None:
        """LLM returning 8 actions raises ValueError before any DB write."""
        fake_llm = FakeLLMProvider()
        generated = _make_generated_protocol(num_actions=8, minutes_per_action=5)
        fake_llm.generate = AsyncMock(return_value=generated)  # type: ignore[method-assign]

        ctx = FakeContextProvider(lifestyle=_make_lifestyle(time_budget=60))
        svc, proto_repo, action_repo = await self._make_service(fake_llm, ctx)

        with pytest.raises(ValueError, match="actions"):
            await svc.generate_for_patient("PT_TEST")

        # No DB writes should have occurred
        assert len(proto_repo.created) == 0
        assert len(action_repo.added) == 0

    async def test_empty_actions_raises_value_error(self) -> None:
        """LLM returning 0 actions raises ValueError before any DB write."""
        fake_llm = FakeLLMProvider()
        generated = _make_generated_protocol(num_actions=0)
        fake_llm.generate = AsyncMock(return_value=generated)  # type: ignore[method-assign]

        ctx = FakeContextProvider(lifestyle=_make_lifestyle(time_budget=60))
        svc, proto_repo, action_repo = await self._make_service(fake_llm, ctx)

        with pytest.raises(ValueError, match="actions"):
            await svc.generate_for_patient("PT_TEST")

        assert len(proto_repo.created) == 0
        assert len(action_repo.added) == 0

    async def test_time_budget_exceeded_raises_value_error(self) -> None:
        """Actions summing to more than time_budget_minutes_per_day → ValueError."""
        fake_llm = FakeLLMProvider()
        # 4 actions × 20 min = 80 min total; budget is 60
        generated = _make_generated_protocol(num_actions=4, minutes_per_action=20)
        fake_llm.generate = AsyncMock(return_value=generated)  # type: ignore[method-assign]

        ctx = FakeContextProvider(lifestyle=_make_lifestyle(time_budget=60))
        svc, proto_repo, action_repo = await self._make_service(fake_llm, ctx)

        with pytest.raises(ValueError, match="time_budget"):
            await svc.generate_for_patient("PT_TEST")

        assert len(proto_repo.created) == 0
        assert len(action_repo.added) == 0

    async def test_time_budget_exactly_met_succeeds(self) -> None:
        """Actions summing exactly to budget passes the constraint check."""
        fake_llm = FakeLLMProvider()
        # 3 actions × 20 min = 60 min = budget
        generated = _make_generated_protocol(num_actions=3, minutes_per_action=20)
        fake_llm.generate = AsyncMock(return_value=generated)  # type: ignore[method-assign]

        ctx = FakeContextProvider(lifestyle=_make_lifestyle(time_budget=60))
        svc, proto_repo, _ = await self._make_service(fake_llm, ctx)

        result = await svc.generate_for_patient("PT_TEST")
        assert result is not None
        assert len(proto_repo.created) == 1

    async def test_no_lifestyle_profile_raises_value_error(self) -> None:
        """Missing LifestyleProfile for patient → ValueError."""
        fake_llm = FakeLLMProvider()
        fake_llm.generate = AsyncMock(return_value=_make_generated_protocol())  # type: ignore[method-assign]

        ctx = FakeContextProvider(lifestyle=None)  # type: ignore[arg-type]
        # Override so lifestyle is None
        ctx.lifestyle = None  # type: ignore[assignment]
        svc, _, _ = await self._make_service(fake_llm, ctx)

        with pytest.raises(ValueError, match="LifestyleProfile"):
            await svc.generate_for_patient("PT_TEST")

    async def test_protocol_action_data_mapped_correctly(self) -> None:
        """ProtocolAction rows carry title, category, rationale from LLM output."""
        fake_llm = FakeLLMProvider()
        generated: dict[str, Any] = {
            "rationale": "Focus week.",
            "actions": [
                {
                    "category": "sleep",
                    "title": "Early bedtime",
                    "target": "22:30",
                    "rationale": "Better sleep onset",
                    "dimension": "sleep_recovery",
                    "estimated_minutes": 10,
                }
            ],
        }
        fake_llm.generate = AsyncMock(return_value=generated)  # type: ignore[method-assign]

        ctx = FakeContextProvider(lifestyle=_make_lifestyle(time_budget=60))
        svc, _, action_repo = await self._make_service(fake_llm, ctx)

        await svc.generate_for_patient("PT_TEST")

        action = action_repo.added[0]
        assert action.category == "sleep"
        assert action.title == "Early bedtime"
        assert action.rationale == "Better sleep onset"
        assert action.target_value == "22:30"
