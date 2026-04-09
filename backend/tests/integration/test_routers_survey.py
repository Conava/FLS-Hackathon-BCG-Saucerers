"""Integration tests for the /v1/patients/{patient_id}/survey endpoints.

Uses the mini-app-factory pattern: a minimal FastAPI app is built per fixture,
overriding ``get_session`` with the testcontainers-backed ``db_session``.

Test matrix:
  - POST /v1/patients/{pid}/survey — happy path for each kind
  - POST onboarding — updates LifestyleProfile fields from answers
  - GET /v1/patients/{pid}/survey?kind=... — latest by kind, 404 if none
  - GET /v1/patients/{pid}/survey/history?kind=... — full history list
  - Cross-patient isolation — PT0001 cannot see PT0002's surveys
  - Auth enforcement — 401 without X-API-Key
"""

from __future__ import annotations

import datetime

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

HEADERS = {"X-API-Key": "test-key"}


# ---------------------------------------------------------------------------
# Mini app factory fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session")
async def survey_client(db_session: AsyncSession) -> AsyncClient:  # type: ignore[return]
    """Minimal FastAPI app wired to the test ``db_session``.

    Only the survey router is mounted (plus health for sanity).  The session
    override ensures every HTTP call shares the per-test transaction so it
    will be rolled back after each test.
    """
    from fastapi import FastAPI
    from httpx import AsyncClient
    from httpx._transports.asgi import ASGITransport

    from app.db.session import get_session
    from app.routers import health, survey

    app = FastAPI()
    app.include_router(health.router)
    app.include_router(survey.router, prefix="/v1")

    async def _override():  # type: ignore[return]
        yield db_session

    app.dependency_overrides[get_session] = _override

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


async def _seed_patient(
    session: AsyncSession,
    patient_id: str,
    name: str = "Test Patient",
) -> None:
    """Insert a minimal Patient row and flush."""
    from app.models.patient import Patient

    p = Patient(
        patient_id=patient_id,
        name=name,
        age=35,
        sex="unknown",
        country="DE",
    )
    session.add(p)
    await session.flush()


async def _seed_lifestyle(
    session: AsyncSession,
    patient_id: str,
) -> None:
    """Insert a minimal LifestyleProfile row for the patient."""
    from app.models.lifestyle_profile import LifestyleProfile

    lp = LifestyleProfile(
        patient_id=patient_id,
        survey_date=datetime.date(2026, 1, 1),
        smoking_status="never",
        alcohol_units_weekly=0.0,
    )
    session.add(lp)
    await session.flush()


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------


async def test_post_survey_requires_api_key(
    survey_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /survey without X-API-Key must return 401."""
    await _seed_patient(db_session, "PT_S001")

    resp = await survey_client.post(
        "/v1/patients/PT_S001/survey",
        json={"kind": "weekly", "answers": {}},
    )
    assert resp.status_code == 401


async def test_get_survey_requires_api_key(
    survey_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /survey without X-API-Key must return 401."""
    await _seed_patient(db_session, "PT_S002")

    resp = await survey_client.get(
        "/v1/patients/PT_S002/survey",
        params={"kind": "weekly"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /v1/patients/{patient_id}/survey — happy path
# ---------------------------------------------------------------------------


async def test_post_weekly_survey_persists_and_returns_201(
    survey_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Posting a weekly survey returns 201 with the persisted response."""
    await _seed_patient(db_session, "PT_S010")

    payload = {
        "kind": "weekly",
        "answers": {"energy_level": 7, "protocol_adherence": True},
    }
    resp = await survey_client.post(
        "/v1/patients/PT_S010/survey",
        json=payload,
        headers=HEADERS,
    )
    assert resp.status_code == 201, resp.text

    data = resp.json()
    assert data["patient_id"] == "PT_S010"
    assert data["kind"] == "weekly"
    assert data["id"] is not None
    assert data["answers"]["energy_level"] == 7


async def test_post_quarterly_survey_persists(
    survey_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Posting a quarterly survey returns 201 with correct kind."""
    await _seed_patient(db_session, "PT_S011")

    resp = await survey_client.post(
        "/v1/patients/PT_S011/survey",
        json={"kind": "quarterly", "answers": {"goal": "longevity"}},
        headers=HEADERS,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["kind"] == "quarterly"


async def test_post_onboarding_survey_persists(
    survey_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Posting an onboarding survey returns 201."""
    await _seed_patient(db_session, "PT_S012")

    resp = await survey_client.post(
        "/v1/patients/PT_S012/survey",
        json={
            "kind": "onboarding",
            "answers": {
                "time_budget_minutes_per_day": 30,
                "out_of_pocket_budget_eur_per_month": 50.0,
            },
        },
        headers=HEADERS,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["kind"] == "onboarding"


async def test_post_onboarding_updates_lifestyle_profile(
    survey_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Posting onboarding survey with lifestyle fields updates LifestyleProfile."""
    from sqlalchemy import select

    from app.models.lifestyle_profile import LifestyleProfile

    await _seed_patient(db_session, "PT_S020")
    await _seed_lifestyle(db_session, "PT_S020")

    resp = await survey_client.post(
        "/v1/patients/PT_S020/survey",
        json={
            "kind": "onboarding",
            "answers": {
                "time_budget_minutes_per_day": 45,
                "out_of_pocket_budget_eur_per_month": 100.0,
                "dietary_restrictions": "vegan",
                "known_allergies": "peanuts",
                "injuries_or_limitations": "bad knee",
            },
        },
        headers=HEADERS,
    )
    assert resp.status_code == 201, resp.text

    # Verify LifestyleProfile was updated.
    pid_attr = getattr(LifestyleProfile, "patient_id")
    stmt = select(LifestyleProfile).where(pid_attr == "PT_S020")
    result = await db_session.execute(stmt)
    lp = result.scalars().first()
    assert lp is not None
    assert lp.time_budget_minutes_per_day == 45
    assert lp.out_of_pocket_budget_eur_per_month == 100.0
    assert lp.dietary_restrictions == "vegan"
    assert lp.known_allergies == "peanuts"
    assert lp.injuries_or_limitations == "bad knee"


async def test_post_onboarding_creates_lifestyle_profile_if_missing(
    survey_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Posting onboarding when no LifestyleProfile exists creates one."""
    from sqlalchemy import select

    from app.models.lifestyle_profile import LifestyleProfile

    await _seed_patient(db_session, "PT_S021")
    # No lifestyle profile seeded intentionally.

    resp = await survey_client.post(
        "/v1/patients/PT_S021/survey",
        json={
            "kind": "onboarding",
            "answers": {
                "time_budget_minutes_per_day": 20,
            },
        },
        headers=HEADERS,
    )
    assert resp.status_code == 201, resp.text

    pid_attr = getattr(LifestyleProfile, "patient_id")
    stmt = select(LifestyleProfile).where(pid_attr == "PT_S021")
    result = await db_session.execute(stmt)
    lp = result.scalars().first()
    assert lp is not None
    assert lp.time_budget_minutes_per_day == 20


async def test_post_survey_returns_404_for_unknown_patient(
    survey_client: AsyncClient,
) -> None:
    """Posting a survey for a non-existent patient returns 404."""
    resp = await survey_client.post(
        "/v1/patients/PT_GHOST/survey",
        json={"kind": "weekly", "answers": {}},
        headers=HEADERS,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /v1/patients/{patient_id}/survey?kind=... — latest by kind
# ---------------------------------------------------------------------------


async def test_get_latest_survey_returns_most_recent(
    survey_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /survey?kind=weekly returns the most recently submitted weekly survey."""
    await _seed_patient(db_session, "PT_S030")

    # Post two weekly surveys sequentially; the second should be returned.
    await survey_client.post(
        "/v1/patients/PT_S030/survey",
        json={"kind": "weekly", "answers": {"energy_level": 5}},
        headers=HEADERS,
    )
    resp2 = await survey_client.post(
        "/v1/patients/PT_S030/survey",
        json={"kind": "weekly", "answers": {"energy_level": 8}},
        headers=HEADERS,
    )
    assert resp2.status_code == 201

    resp = await survey_client.get(
        "/v1/patients/PT_S030/survey",
        params={"kind": "weekly"},
        headers=HEADERS,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["patient_id"] == "PT_S030"
    assert data["kind"] == "weekly"
    # Most recent has energy_level=8.
    assert data["answers"]["energy_level"] == 8


async def test_get_latest_survey_404_when_none_exist(
    survey_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /survey?kind=quarterly returns 404 when no quarterly surveys exist."""
    await _seed_patient(db_session, "PT_S031")

    resp = await survey_client.get(
        "/v1/patients/PT_S031/survey",
        params={"kind": "quarterly"},
        headers=HEADERS,
    )
    assert resp.status_code == 404


async def test_get_latest_survey_404_unknown_patient(
    survey_client: AsyncClient,
) -> None:
    """GET /survey?kind=weekly for an unknown patient returns 404."""
    resp = await survey_client.get(
        "/v1/patients/PT_GHOST/survey",
        params={"kind": "weekly"},
        headers=HEADERS,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /v1/patients/{patient_id}/survey/history?kind=... — history
# ---------------------------------------------------------------------------


async def test_get_survey_history_returns_all_in_desc_order(
    survey_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /survey/history?kind=weekly returns all weekly surveys, newest first."""
    await _seed_patient(db_session, "PT_S040")

    # Post three weekly surveys.
    for energy in (3, 6, 9):
        await survey_client.post(
            "/v1/patients/PT_S040/survey",
            json={"kind": "weekly", "answers": {"energy_level": energy}},
            headers=HEADERS,
        )

    resp = await survey_client.get(
        "/v1/patients/PT_S040/survey/history",
        params={"kind": "weekly"},
        headers=HEADERS,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["patient_id"] == "PT_S040"
    responses = data["responses"]
    assert len(responses) == 3
    # Newest first — energy_level 9 was submitted last.
    assert responses[0]["answers"]["energy_level"] == 9


async def test_get_survey_history_empty_list_for_unknown_kind(
    survey_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /survey/history returns an empty list when no surveys of that kind exist."""
    await _seed_patient(db_session, "PT_S041")

    resp = await survey_client.get(
        "/v1/patients/PT_S041/survey/history",
        params={"kind": "quarterly"},
        headers=HEADERS,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["responses"] == []


async def test_get_survey_history_requires_api_key(
    survey_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /survey/history without API key returns 401."""
    await _seed_patient(db_session, "PT_S042")

    resp = await survey_client.get(
        "/v1/patients/PT_S042/survey/history",
        params={"kind": "weekly"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Cross-patient isolation
# ---------------------------------------------------------------------------


async def test_cross_patient_isolation_get_latest(
    survey_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Surveys submitted for PT_ISO_A are invisible when querying as PT_ISO_B."""
    await _seed_patient(db_session, "PT_ISO_A")
    await _seed_patient(db_session, "PT_ISO_B")

    # Post a quarterly survey for PT_ISO_A.
    post_resp = await survey_client.post(
        "/v1/patients/PT_ISO_A/survey",
        json={"kind": "quarterly", "answers": {"secret": "patient_a_data"}},
        headers=HEADERS,
    )
    assert post_resp.status_code == 201

    # PT_ISO_B has no quarterly surveys; querying as PT_ISO_B must return 404.
    resp = await survey_client.get(
        "/v1/patients/PT_ISO_B/survey",
        params={"kind": "quarterly"},
        headers=HEADERS,
    )
    assert resp.status_code == 404, (
        "Cross-patient isolation violated: PT_ISO_B received PT_ISO_A's survey data"
    )


async def test_cross_patient_isolation_history(
    survey_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """History for PT_ISO_C does not contain surveys submitted for PT_ISO_D."""
    await _seed_patient(db_session, "PT_ISO_C")
    await _seed_patient(db_session, "PT_ISO_D")

    # Post a weekly survey for PT_ISO_D only.
    await survey_client.post(
        "/v1/patients/PT_ISO_D/survey",
        json={"kind": "weekly", "answers": {"energy_level": 10}},
        headers=HEADERS,
    )

    # PT_ISO_C's history must be empty.
    resp = await survey_client.get(
        "/v1/patients/PT_ISO_C/survey/history",
        params={"kind": "weekly"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["responses"] == [], (
        "Cross-patient isolation violated: PT_ISO_C received PT_ISO_D's survey history"
    )
