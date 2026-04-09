"""Integration tests for the /patients/{patient_id}/appointments endpoints.

Uses the same mini-app-factory pattern as test_routers_patients.py.
The AppointmentSource is the router's built-in fallback stub so no T15
dependency is required.
"""

from __future__ import annotations

import os

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://ignored")

HEADERS = {"X-API-Key": "test-key"}


# ---------------------------------------------------------------------------
# Mini app factory fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session")
async def appointments_client(db_session: AsyncSession) -> AsyncClient:  # type: ignore[return]
    """Minimal FastAPI app wired to the test ``db_session``."""
    from fastapi import FastAPI
    from httpx import AsyncClient
    from httpx._transports.asgi import ASGITransport

    from app.db.session import get_session
    from app.routers import appointments, health, patients

    app = FastAPI()
    app.include_router(health.router)
    app.include_router(patients.router)
    app.include_router(appointments.router)

    async def _override():  # type: ignore[return]
        yield db_session

    app.dependency_overrides[get_session] = _override

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Seed helper
# ---------------------------------------------------------------------------


async def _seed_patient(session: AsyncSession, patient_id: str, name: str) -> None:
    from app.models.patient import Patient

    p = Patient(
        patient_id=patient_id,
        name=name,
        age=40,
        sex="female",
        country="Germany",
    )
    session.add(p)
    await session.flush()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_get_appointments_returns_stub_list(
    appointments_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """PT0282 should receive 2 appointments from the stub."""
    await _seed_patient(db_session, "PT0282", "Anna Weber")

    resp = await appointments_client.get(
        "/patients/PT0282/appointments/",
        headers=HEADERS,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["patient_id"] == "PT0282"
    appointments = data["appointments"]
    # Stub returns 2 for PT0282.
    assert len(appointments) == 2
    # Each appointment must have required fields.
    for appt in appointments:
        assert "id" in appt
        assert "title" in appt
        assert "provider" in appt
        assert "starts_at" in appt
        assert "duration_minutes" in appt


async def test_get_appointments_returns_one_for_other_patients(
    appointments_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Non-PT0282 patients should receive 1 appointment from the stub."""
    await _seed_patient(db_session, "PT0001", "Max Mustermann")

    resp = await appointments_client.get(
        "/patients/PT0001/appointments/",
        headers=HEADERS,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["appointments"]) == 1


async def test_get_appointments_404_for_unknown_patient(
    appointments_client: AsyncClient,
) -> None:
    """Requesting appointments for an unknown patient must return 404."""
    resp = await appointments_client.get(
        "/patients/PT9999/appointments/",
        headers=HEADERS,
    )
    assert resp.status_code == 404


async def test_get_appointments_requires_api_key(
    appointments_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Appointments endpoint must reject requests without X-API-Key."""
    await _seed_patient(db_session, "PT0282", "Anna Weber")

    resp = await appointments_client.get("/patients/PT0282/appointments/")
    assert resp.status_code == 401
