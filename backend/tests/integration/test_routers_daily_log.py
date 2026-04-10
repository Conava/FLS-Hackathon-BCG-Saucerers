"""Integration tests for POST/GET /v1/patients/{patient_id}/daily-log.

Uses the mini-app-factory fixture pattern so this test module is independent
of T23b (main.py wiring).  The fixture overrides ``get_session`` with the
testcontainers-backed ``db_session``.

Test coverage:
  - POST happy path — 201 with correct fields echoed back
  - GET happy path — returns logs within date range
  - GET date-range filtering — logs outside range are excluded
  - Cross-patient isolation — POST and GET never leak across patients
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
async def daily_log_client(db_session: AsyncSession) -> AsyncClient:  # type: ignore[return]
    """Build a minimal FastAPI app with the daily-log router wired in."""
    from fastapi import FastAPI
    from httpx import AsyncClient
    from httpx._transports.asgi import ASGITransport

    from app.db.session import get_session
    from app.routers import daily_log

    app = FastAPI()
    app.include_router(daily_log.router, prefix="/v1")

    async def _override():  # type: ignore[return]
        yield db_session

    app.dependency_overrides[get_session] = _override

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Seed helper
# ---------------------------------------------------------------------------


async def _seed_patient(session: AsyncSession, patient_id: str, name: str) -> None:
    """Insert a minimal Patient row so FK constraints are satisfied."""
    from app.models.patient import Patient

    p = Patient(
        patient_id=patient_id,
        name=name,
        age=35,
        sex="female",
        country="Germany",
    )
    session.add(p)
    await session.flush()


# ---------------------------------------------------------------------------
# POST /v1/patients/{patient_id}/daily-log — happy path
# ---------------------------------------------------------------------------


async def test_post_daily_log_creates_entry(
    daily_log_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST a full daily log payload; expect 201 with all fields reflected."""
    await _seed_patient(db_session, "PT0100", "Test Patient")

    payload = {
        "date": "2026-04-09",
        "mood_score": 7,
        "workout_minutes": 30,
        "sleep_hours": 7.5,
        "water_glasses": 8,
        "alcohol_units": 1,
    }
    resp = await daily_log_client.post(
        "/v1/patients/PT0100/daily-log",
        json=payload,
        headers=HEADERS,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert data["patient_id"] == "PT0100"
    assert data["date"] == "2026-04-09"
    assert data["mood_score"] == 7
    assert data["workout_minutes"] == 30
    assert data["sleep_hours"] == pytest.approx(7.5, abs=0.01)
    assert data["water_glasses"] == 8
    assert data["alcohol_units"] == 1
    assert "id" in data
    assert "logged_at" in data
    # New structured fields are null when not provided
    assert data["sleep_quality"] is None
    assert data["workout_type"] is None
    assert data["workout_intensity"] is None


async def test_post_daily_log_partial_fields(
    daily_log_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST with only mood_score — all other metric fields must be null."""
    await _seed_patient(db_session, "PT0101", "Partial Logger")

    payload = {
        "date": "2026-04-09",
        "mood_score": 5,
    }
    resp = await daily_log_client.post(
        "/v1/patients/PT0101/daily-log",
        json=payload,
        headers=HEADERS,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert data["mood_score"] == 5
    assert data["workout_minutes"] is None
    assert data["sleep_hours"] is None
    assert data["water_glasses"] is None
    assert data["alcohol_units"] is None


# ---------------------------------------------------------------------------
# GET /v1/patients/{patient_id}/daily-log — happy path
# ---------------------------------------------------------------------------


async def test_get_daily_log_returns_entries_within_range(
    daily_log_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET returns all entries whose date falls within the from/to window."""
    await _seed_patient(db_session, "PT0102", "Range Tester")

    # Post three entries on different days
    for day_offset, mood in enumerate([6, 7, 8], start=1):
        log_date = f"2026-04-0{day_offset}"
        await daily_log_client.post(
            "/v1/patients/PT0102/daily-log",
            json={"date": log_date, "mood_score": mood},
            headers=HEADERS,
        )

    resp = await daily_log_client.get(
        "/v1/patients/PT0102/daily-log",
        params={"from": "2026-04-01", "to": "2026-04-03"},
        headers=HEADERS,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["patient_id"] == "PT0102"
    logs = data["logs"]
    assert len(logs) == 3
    # Ordered ascending by logged_at
    mood_scores = [l["mood_score"] for l in logs]
    assert mood_scores == [6, 7, 8]


async def test_get_daily_log_filters_out_of_range(
    daily_log_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET must exclude entries outside the requested date window."""
    await _seed_patient(db_session, "PT0103", "Filter Tester")

    # Post entries on 2026-04-01, 2026-04-05, 2026-04-10
    for log_date in ["2026-04-01", "2026-04-05", "2026-04-10"]:
        await daily_log_client.post(
            "/v1/patients/PT0103/daily-log",
            json={"date": log_date, "mood_score": 5},
            headers=HEADERS,
        )

    resp = await daily_log_client.get(
        "/v1/patients/PT0103/daily-log",
        params={"from": "2026-04-04", "to": "2026-04-06"},
        headers=HEADERS,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    logs = data["logs"]
    assert len(logs) == 1
    assert logs[0]["date"] == "2026-04-05"


async def test_get_daily_log_empty_range_returns_empty_list(
    daily_log_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET with a date range that has no logs returns an empty logs list."""
    await _seed_patient(db_session, "PT0104", "Empty Range")

    resp = await daily_log_client.get(
        "/v1/patients/PT0104/daily-log",
        params={"from": "2026-01-01", "to": "2026-01-31"},
        headers=HEADERS,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["patient_id"] == "PT0104"
    assert data["logs"] == []


# ---------------------------------------------------------------------------
# Cross-patient isolation
# ---------------------------------------------------------------------------


async def test_post_daily_log_isolation_other_patient_sees_nothing(
    daily_log_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Logs created for PT0110 must NOT appear when querying PT0111."""
    await _seed_patient(db_session, "PT0110", "Patient A")
    await _seed_patient(db_session, "PT0111", "Patient B")

    # Create a log for PT0110
    await daily_log_client.post(
        "/v1/patients/PT0110/daily-log",
        json={"date": "2026-04-09", "mood_score": 9},
        headers=HEADERS,
    )

    # Query PT0111 — should be empty
    resp = await daily_log_client.get(
        "/v1/patients/PT0111/daily-log",
        params={"from": "2026-04-01", "to": "2026-04-30"},
        headers=HEADERS,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["patient_id"] == "PT0111"
    assert data["logs"] == [], "PT0111 must not see PT0110's logs"


async def test_get_daily_log_isolation_only_own_logs_returned(
    daily_log_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Each patient only sees their own logs in the GET response."""
    await _seed_patient(db_session, "PT0112", "Patient C")
    await _seed_patient(db_session, "PT0113", "Patient D")

    # Seed two logs for PT0112 and one for PT0113
    for _ in range(2):
        await daily_log_client.post(
            "/v1/patients/PT0112/daily-log",
            json={"date": "2026-04-09", "mood_score": 7},
            headers=HEADERS,
        )
    await daily_log_client.post(
        "/v1/patients/PT0113/daily-log",
        json={"date": "2026-04-09", "mood_score": 3},
        headers=HEADERS,
    )

    # PT0113 must only see their own 1 log
    resp = await daily_log_client.get(
        "/v1/patients/PT0113/daily-log",
        params={"from": "2026-04-01", "to": "2026-04-30"},
        headers=HEADERS,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["logs"]) == 1
    assert data["logs"][0]["mood_score"] == 3


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------


async def test_post_daily_log_requires_api_key(
    daily_log_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST without X-API-Key must return 401."""
    await _seed_patient(db_session, "PT0120", "Auth Test")

    resp = await daily_log_client.post(
        "/v1/patients/PT0120/daily-log",
        json={"date": "2026-04-09", "mood_score": 5},
    )
    assert resp.status_code == 401


async def test_get_daily_log_requires_api_key(
    daily_log_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET without X-API-Key must return 401."""
    await _seed_patient(db_session, "PT0121", "Auth Test GET")

    resp = await daily_log_client.get(
        "/v1/patients/PT0121/daily-log",
        params={"from": "2026-04-01", "to": "2026-04-30"},
    )
    assert resp.status_code == 401


import pytest


# ---------------------------------------------------------------------------
# B1 — structured sleep + workout fields
# ---------------------------------------------------------------------------


async def test_post_daily_log_sleep_quality_roundtrip(
    daily_log_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST with sleep_hours + sleep_quality persists and is returned via GET."""
    await _seed_patient(db_session, "PT0200", "Sleep Tester")

    payload = {
        "date": "2026-04-09",
        "sleep_hours": 7.5,
        "sleep_quality": 4,
    }
    resp = await daily_log_client.post(
        "/v1/patients/PT0200/daily-log",
        json=payload,
        headers=HEADERS,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["sleep_hours"] == pytest.approx(7.5, abs=0.01)
    assert data["sleep_quality"] == 4

    # Verify via GET
    get_resp = await daily_log_client.get(
        "/v1/patients/PT0200/daily-log",
        params={"from": "2026-04-09", "to": "2026-04-09"},
        headers=HEADERS,
    )
    assert get_resp.status_code == 200, get_resp.text
    logs = get_resp.json()["logs"]
    assert len(logs) == 1
    assert logs[0]["sleep_quality"] == 4


async def test_post_daily_log_workout_fields_roundtrip(
    daily_log_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST with workout_minutes + workout_type + workout_intensity persists and returns."""
    await _seed_patient(db_session, "PT0201", "Workout Tester")

    payload = {
        "date": "2026-04-09",
        "workout_minutes": 30,
        "workout_type": "run",
        "workout_intensity": "med",
    }
    resp = await daily_log_client.post(
        "/v1/patients/PT0201/daily-log",
        json=payload,
        headers=HEADERS,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["workout_minutes"] == 30
    assert data["workout_type"] == "run"
    assert data["workout_intensity"] == "med"

    # Verify via GET
    get_resp = await daily_log_client.get(
        "/v1/patients/PT0201/daily-log",
        params={"from": "2026-04-09", "to": "2026-04-09"},
        headers=HEADERS,
    )
    assert get_resp.status_code == 200, get_resp.text
    logs = get_resp.json()["logs"]
    assert len(logs) == 1
    assert logs[0]["workout_type"] == "run"
    assert logs[0]["workout_intensity"] == "med"


async def test_post_daily_log_omitting_new_fields_stays_backwards_compatible(
    daily_log_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST without the new fields must succeed and return nulls for them."""
    await _seed_patient(db_session, "PT0202", "Compat Tester")

    payload = {
        "date": "2026-04-09",
        "mood_score": 6,
        "sleep_hours": 8.0,
    }
    resp = await daily_log_client.post(
        "/v1/patients/PT0202/daily-log",
        json=payload,
        headers=HEADERS,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["sleep_quality"] is None
    assert data["workout_type"] is None
    assert data["workout_intensity"] is None


async def test_post_daily_log_sleep_quality_validation(
    daily_log_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """sleep_quality outside 1-5 range must be rejected with 422."""
    await _seed_patient(db_session, "PT0203", "Validation Tester")

    payload = {
        "date": "2026-04-09",
        "sleep_quality": 6,  # out of range
    }
    resp = await daily_log_client.post(
        "/v1/patients/PT0203/daily-log",
        json=payload,
        headers=HEADERS,
    )
    assert resp.status_code == 422, resp.text


async def test_post_daily_log_workout_type_validation(
    daily_log_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """workout_type with invalid value must be rejected with 422."""
    await _seed_patient(db_session, "PT0204", "WType Validation Tester")

    payload = {
        "date": "2026-04-09",
        "workout_type": "swimming",  # not in allowed set
    }
    resp = await daily_log_client.post(
        "/v1/patients/PT0204/daily-log",
        json=payload,
        headers=HEADERS,
    )
    assert resp.status_code == 422, resp.text


async def test_post_daily_log_workout_intensity_validation(
    daily_log_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """workout_intensity with invalid value must be rejected with 422."""
    await _seed_patient(db_session, "PT0205", "WIntensity Validation Tester")

    payload = {
        "date": "2026-04-09",
        "workout_intensity": "extreme",  # not in allowed set
    }
    resp = await daily_log_client.post(
        "/v1/patients/PT0205/daily-log",
        json=payload,
        headers=HEADERS,
    )
    assert resp.status_code == 422, resp.text
