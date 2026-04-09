"""Integration tests for the /v1/patients/{patient_id}/protocol endpoints.

Uses the mini-app-factory pattern matching existing Slice 1 router tests.
The fixture overrides ``get_session`` with the testcontainers-backed
``db_session`` and injects ``FakeLLMProvider`` with mocked ``generate`` so
no real LLM calls are made.

Seeded data:
  - PT_R17A: primary patient used in most assertions.
  - PT_R17B: secondary patient for cross-patient isolation checks.

Endpoints tested:
  - POST /v1/patients/{patient_id}/protocol/generate
  - GET  /v1/patients/{patient_id}/protocol
  - POST /v1/patients/{patient_id}/protocol/complete-action
"""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

HEADERS = {"X-API-Key": "test-key"}


# ---------------------------------------------------------------------------
# Helpers for generating a valid protocol dict (mirrors test_protocol_generator)
# ---------------------------------------------------------------------------


def _make_generated_protocol(
    num_actions: int = 3,
    minutes_per_action: int = 15,
) -> dict:
    """Return a valid GeneratedProtocol-shaped dict for FakeLLMProvider mock."""
    actions = [
        {
            "category": "movement",
            "title": f"Action {i + 1}",
            "target": f"{minutes_per_action} min",
            "rationale": f"Rationale {i + 1}",
            "dimension": "cardio_fitness",
        }
        for i in range(num_actions)
    ]
    return {
        "rationale": "Weekly movement focus.",
        "actions": actions,
    }


# ---------------------------------------------------------------------------
# Mini app factory fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session")
async def protocol_client(db_session: AsyncSession) -> AsyncClient:  # type: ignore[return]
    """Build a minimal FastAPI app wired to the test ``db_session``.

    Injects ``FakeLLMProvider`` (with a mocked ``generate``) as the LLM
    dependency so no real LLM calls are made during tests.

    ``get_session`` is overridden to yield the test ``db_session`` so every
    HTTP call participates in the per-test transaction.
    """
    from fastapi import FastAPI
    from httpx import AsyncClient
    from httpx._transports.asgi import ASGITransport

    from app.ai.llm import FakeLLMProvider
    from app.db.session import get_session
    from app.routers import protocol as protocol_router_module

    app = FastAPI()
    app.include_router(protocol_router_module.router, prefix="/v1")

    async def _override():  # type: ignore[return]
        yield db_session

    # Override session dependency
    app.dependency_overrides[get_session] = _override

    # Override the LLM provider dependency with a pre-configured FakeLLMProvider
    fake_llm = FakeLLMProvider()
    fake_llm.generate = AsyncMock(  # type: ignore[method-assign]
        return_value=_make_generated_protocol(num_actions=3, minutes_per_action=15)
    )

    app.dependency_overrides[protocol_router_module.get_llm] = lambda: fake_llm

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# DB seed helpers
# ---------------------------------------------------------------------------


async def _seed_patient_with_lifestyle(
    session: AsyncSession,
    patient_id: str,
    name: str = "Test Patient",
    time_budget: int = 60,
) -> None:
    """Seed a Patient + LifestyleProfile row (required by generate endpoint)."""
    import datetime

    from app.models.lifestyle_profile import LifestyleProfile
    from app.models.patient import Patient

    patient = Patient(
        patient_id=patient_id,
        name=name,
        age=40,
        sex="female",
        country="Germany",
    )
    session.add(patient)
    await session.flush()

    lp = LifestyleProfile(
        patient_id=patient_id,
        survey_date=datetime.date(2026, 4, 7),
        diet_quality_score=7,
        time_budget_minutes_per_day=time_budget,
    )
    session.add(lp)
    await session.flush()


async def _generate_protocol_for(
    client: AsyncClient,
    patient_id: str,
) -> dict:
    """Call the generate endpoint and return the JSON response."""
    resp = await client.post(
        f"/v1/patients/{patient_id}/protocol/generate",
        headers=HEADERS,
    )
    assert resp.status_code == 200, f"generate failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# POST /v1/patients/{patient_id}/protocol/generate — happy path
# ---------------------------------------------------------------------------


async def test_generate_protocol_returns_protocol_out(
    protocol_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST generate must return a ProtocolOut with id, patient_id, created_at, actions."""
    await _seed_patient_with_lifestyle(db_session, "PT_R17A", "Alice Router")

    data = await _generate_protocol_for(protocol_client, "PT_R17A")

    assert data["patient_id"] == "PT_R17A"
    assert "id" in data
    assert "created_at" in data
    assert isinstance(data["actions"], list)
    assert len(data["actions"]) == 3

    action = data["actions"][0]
    assert action["category"] == "movement"
    assert action["title"] == "Action 1"


async def test_generate_protocol_404_for_missing_lifestyle(
    protocol_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST generate must return 422/500-ish when LifestyleProfile is missing.

    The service raises ValueError; the router must surface this as HTTP 422.
    """
    from app.models.patient import Patient

    patient = Patient(patient_id="PT_R17_NLP", name="No Lifestyle", age=30, sex="male", country="DE")
    db_session.add(patient)
    await db_session.flush()

    resp = await protocol_client.post(
        "/v1/patients/PT_R17_NLP/protocol/generate",
        headers=HEADERS,
    )
    # Service raises ValueError → router returns 422 Unprocessable
    assert resp.status_code == 422


async def test_generate_protocol_requires_api_key(
    protocol_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST generate must reject requests without X-API-Key with 401."""
    await _seed_patient_with_lifestyle(db_session, "PT_R17_AUTH")

    resp = await protocol_client.post("/v1/patients/PT_R17_AUTH/protocol/generate")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /v1/patients/{patient_id}/protocol — happy path
# ---------------------------------------------------------------------------


async def test_get_protocol_returns_active_protocol(
    protocol_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET protocol must return the active protocol for the patient."""
    await _seed_patient_with_lifestyle(db_session, "PT_R17B", "Bob Router")

    # Generate first, then retrieve
    generated = await _generate_protocol_for(protocol_client, "PT_R17B")
    generated_id = generated["id"]

    resp = await protocol_client.get(
        "/v1/patients/PT_R17B/protocol",
        headers=HEADERS,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["id"] == generated_id
    assert data["patient_id"] == "PT_R17B"
    assert isinstance(data["actions"], list)
    assert len(data["actions"]) >= 1


async def test_get_protocol_404_when_none_exists(
    protocol_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET protocol must return 404 when the patient has no active protocol."""
    from app.models.patient import Patient

    patient = Patient(patient_id="PT_R17_NOP", name="No Protocol", age=35, sex="male", country="DE")
    db_session.add(patient)
    await db_session.flush()

    resp = await protocol_client.get(
        "/v1/patients/PT_R17_NOP/protocol",
        headers=HEADERS,
    )
    assert resp.status_code == 404


async def test_get_protocol_requires_api_key(
    protocol_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET protocol must reject requests without X-API-Key with 401."""
    await _seed_patient_with_lifestyle(db_session, "PT_R17_GAUTH")
    await _generate_protocol_for(protocol_client, "PT_R17_GAUTH")

    resp = await protocol_client.get("/v1/patients/PT_R17_GAUTH/protocol")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /v1/patients/{patient_id}/protocol/complete-action — happy path
# ---------------------------------------------------------------------------


async def test_complete_action_updates_streak(
    protocol_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST complete-action must update streak_days and return CompleteActionResponse."""
    await _seed_patient_with_lifestyle(db_session, "PT_R17C", "Carol Router")

    generated = await _generate_protocol_for(protocol_client, "PT_R17C")
    action_id = generated["actions"][0]["id"]

    resp = await protocol_client.post(
        "/v1/patients/PT_R17C/protocol/complete-action",
        headers=HEADERS,
        json={"action_id": action_id},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["action_id"] == action_id
    assert data["streak_days"] == 1  # first completion → streak=1
    assert "completed_at" in data


async def test_complete_action_triggers_outlook_recompute(
    protocol_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST complete-action must persist VitalityOutlook rows (3, 6, 12 month horizons)."""
    from sqlalchemy import select

    from app.models.vitality_outlook import VitalityOutlook

    await _seed_patient_with_lifestyle(db_session, "PT_R17D", "Dave Router")

    generated = await _generate_protocol_for(protocol_client, "PT_R17D")
    action_id = generated["actions"][0]["id"]

    resp = await protocol_client.post(
        "/v1/patients/PT_R17D/protocol/complete-action",
        headers=HEADERS,
        json={"action_id": action_id},
    )
    assert resp.status_code == 200, resp.text

    # Outlook rows should have been persisted for this patient
    pid_attr = getattr(VitalityOutlook, "patient_id")
    stmt = select(VitalityOutlook).where(pid_attr == "PT_R17D")
    result = await db_session.execute(stmt)
    outlook_rows = list(result.scalars().all())

    # compute_outlook returns 3 horizons (3, 6, 12 months)
    assert len(outlook_rows) == 3
    horizons = {row.horizon_months for row in outlook_rows}
    assert horizons == {3, 6, 12}


async def test_complete_action_requires_api_key(
    protocol_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST complete-action must reject requests without X-API-Key with 401."""
    await _seed_patient_with_lifestyle(db_session, "PT_R17_CAUTH")
    generated = await _generate_protocol_for(protocol_client, "PT_R17_CAUTH")
    action_id = generated["actions"][0]["id"]

    resp = await protocol_client.post(
        "/v1/patients/PT_R17_CAUTH/protocol/complete-action",
        json={"action_id": action_id},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Cross-patient isolation
# ---------------------------------------------------------------------------


async def test_complete_action_cross_patient_isolation_returns_404(
    protocol_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Completing patient A's action via patient B's path must return 404.

    This verifies the two-step isolation pattern in ProtocolActionRepository:
    patient B cannot access an action that belongs to patient A's protocol.
    """
    # Seed both patients
    await _seed_patient_with_lifestyle(db_session, "PT_R17_ISO_A", "Isolation A")
    await _seed_patient_with_lifestyle(db_session, "PT_R17_ISO_B", "Isolation B")

    # Generate a protocol for patient A
    generated_a = await _generate_protocol_for(protocol_client, "PT_R17_ISO_A")
    action_id_a = generated_a["actions"][0]["id"]

    # Attempt to complete patient A's action via patient B's path → must 404
    resp = await protocol_client.post(
        "/v1/patients/PT_R17_ISO_B/protocol/complete-action",
        headers=HEADERS,
        json={"action_id": action_id_a},
    )
    assert resp.status_code == 404, (
        f"Expected 404 when completing patient A's action via patient B's path, "
        f"got {resp.status_code}: {resp.text}"
    )


async def test_get_protocol_cross_patient_isolation(
    protocol_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET protocol for patient with no protocol returns 404, even when another patient has one."""
    await _seed_patient_with_lifestyle(db_session, "PT_R17_ISO_C", "Isolation C")
    await _seed_patient_with_lifestyle(db_session, "PT_R17_ISO_D", "Isolation D")

    # Only generate for patient C
    await _generate_protocol_for(protocol_client, "PT_R17_ISO_C")

    # Patient D has no protocol — must get 404
    resp = await protocol_client.get(
        "/v1/patients/PT_R17_ISO_D/protocol",
        headers=HEADERS,
    )
    assert resp.status_code == 404
