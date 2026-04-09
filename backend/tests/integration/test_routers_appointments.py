"""Integration tests for the /patients/{patient_id}/appointments endpoints.

Uses the same mini-app-factory pattern as test_routers_patients.py.
The AppointmentSource is the router's built-in fallback stub so no T15
dependency is required.
"""

from __future__ import annotations

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

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
    app.include_router(patients.router, prefix="/v1")
    app.include_router(appointments.router, prefix="/v1")

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
# Existing GET tests (must not regress)
# ---------------------------------------------------------------------------


async def test_get_appointments_returns_stub_list(
    appointments_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """PT0282 should receive 2 appointments from the T15 StaticAppointmentSource."""
    await _seed_patient(db_session, "PT0282", "Anna Weber")

    resp = await appointments_client.get(
        "/v1/patients/PT0282/appointments/",
        headers=HEADERS,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["patient_id"] == "PT0282"
    appointments = data["appointments"]
    # T15 StaticAppointmentSource returns 2 for PT0282.
    assert len(appointments) == 2
    # Each appointment must have required fields.
    for appt in appointments:
        assert "id" in appt
        assert "title" in appt
        assert "provider" in appt
        assert "starts_at" in appt
        assert "duration_minutes" in appt

    # Verify we're actually using T15's StaticAppointmentSource (not fallback).
    # The first appointment should be the T15-specific "Cardio-Prevention Panel".
    titles = [a["title"] for a in appointments]
    assert "Cardio-Prevention Panel" in titles, (
        f"Expected T15 appointment title 'Cardio-Prevention Panel' not found in {titles}. "
        "Silent regression to fallback stub detected."
    )


async def test_get_appointments_returns_one_for_other_patients(
    appointments_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Non-PT0282 patients should receive 1 appointment from the stub."""
    await _seed_patient(db_session, "PT0001", "Max Mustermann")

    resp = await appointments_client.get(
        "/v1/patients/PT0001/appointments/",
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
        "/v1/patients/PT9999/appointments/",
        headers=HEADERS,
    )
    assert resp.status_code == 404


async def test_get_appointments_requires_api_key(
    appointments_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Appointments endpoint must reject requests without X-API-Key."""
    await _seed_patient(db_session, "PT0282", "Anna Weber")

    resp = await appointments_client.get("/v1/patients/PT0282/appointments/")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /v1/patients/{patient_id}/appointments — booking write (T23)
# ---------------------------------------------------------------------------


async def test_post_appointment_creates_booking(
    appointments_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST should create a booking and return the booked AppointmentOut."""
    await _seed_patient(db_session, "PT0100", "Lena Meier")

    payload = {
        "title": "Nutrition Consultation",
        "provider": "Dr. Fischer",
        "location": "Tele-consult",
        "starts_at": "2026-05-10T10:00:00",
        "duration_minutes": 45,
        "price_eur": 60.0,
        "covered_percent": 70,
    }

    resp = await appointments_client.post(
        "/v1/patients/PT0100/appointments/",
        json=payload,
        headers=HEADERS,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()

    # The booked appointment must carry all required AppointmentOut fields.
    assert "id" in data
    assert data["title"] == "Nutrition Consultation"
    assert data["provider"] == "Dr. Fischer"
    assert data["location"] == "Tele-consult"
    assert data["duration_minutes"] == 45
    assert data["price_eur"] == 60.0
    assert data["covered_percent"] == 70


async def test_post_appointment_404_for_unknown_patient(
    appointments_client: AsyncClient,
) -> None:
    """Booking for a non-existent patient must return 404."""
    payload = {
        "title": "Check-up",
        "provider": "Dr. Smith",
        "location": "Clinic",
        "starts_at": "2026-06-01T09:00:00",
        "duration_minutes": 30,
    }

    resp = await appointments_client.post(
        "/v1/patients/PT_UNKNOWN/appointments/",
        json=payload,
        headers=HEADERS,
    )
    assert resp.status_code == 404


async def test_post_appointment_requires_api_key(
    appointments_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST appointments endpoint must reject requests without X-API-Key."""
    await _seed_patient(db_session, "PT0101", "Jonas König")

    payload = {
        "title": "Check-up",
        "provider": "Dr. Smith",
        "location": "Clinic",
        "starts_at": "2026-06-01T09:00:00",
        "duration_minutes": 30,
    }

    resp = await appointments_client.post(
        "/v1/patients/PT0101/appointments/",
        json=payload,
    )
    assert resp.status_code == 401


async def test_post_appointment_cross_patient_isolation(
    appointments_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Cross-patient isolation: POST as patient A; GET as patient B must not see A's booking.

    This asserts that booking an appointment for one patient does not leak into
    another patient's appointment list.  The StaticAppointmentSource is replaced
    with a simple in-memory stub that tracks booked appointments per patient.
    """
    await _seed_patient(db_session, "PT_ISO_A", "Isolde Auer")
    await _seed_patient(db_session, "PT_ISO_B", "Bruno Braun")

    # Book an appointment for patient A with a distinct title.
    payload = {
        "title": "Patient A Private Session",
        "provider": "Dr. Exclusive",
        "location": "Private Clinic",
        "starts_at": "2026-07-01T08:00:00",
        "duration_minutes": 60,
    }

    resp = await appointments_client.post(
        "/v1/patients/PT_ISO_A/appointments/",
        json=payload,
        headers=HEADERS,
    )
    assert resp.status_code == 201, resp.text

    # GET appointments for patient B — must NOT contain patient A's booking.
    resp_b = await appointments_client.get(
        "/v1/patients/PT_ISO_B/appointments/",
        headers=HEADERS,
    )
    assert resp_b.status_code == 200
    titles_b = [a["title"] for a in resp_b.json()["appointments"]]
    assert "Patient A Private Session" not in titles_b, (
        "Cross-patient isolation violated: patient B can see patient A's booking."
    )
