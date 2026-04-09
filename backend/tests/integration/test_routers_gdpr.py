"""Integration tests for the /patients/{patient_id}/gdpr endpoints.

Covers:
  - GET  /patients/{id}/gdpr/export  → GDPRExportOut bundles all data
  - DELETE /patients/{id}/gdpr       → GDPRDeleteAck wellness-framed stub

Uses the same mini-app-factory pattern as test_routers_patients.py.
"""

from __future__ import annotations

import datetime
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
async def gdpr_client(db_session: AsyncSession) -> AsyncClient:  # type: ignore[return]
    """Minimal FastAPI app wired to the test ``db_session``."""
    from fastapi import FastAPI
    from httpx import AsyncClient
    from httpx._transports.asgi import ASGITransport

    from app.db.session import get_session
    from app.routers import appointments, gdpr, health, patients

    app = FastAPI()
    app.include_router(health.router)
    app.include_router(patients.router)
    app.include_router(appointments.router)
    app.include_router(gdpr.router)

    async def _override():  # type: ignore[return]
        yield db_session

    app.dependency_overrides[get_session] = _override

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Seed helper — full Anna profile
# ---------------------------------------------------------------------------


async def _seed_anna_full(session: AsyncSession) -> None:
    """Insert PT0282 with a lab panel, condition, and 3 wearable days."""
    from app.models.ehr_record import EHRRecord
    from app.models.lifestyle_profile import LifestyleProfile
    from app.models.patient import Patient
    from app.models.wearable_day import WearableDay

    anna = Patient(
        patient_id="PT0282",
        name="Anna Weber",
        age=45,
        sex="female",
        country="Germany",
        bmi=24.98,
    )
    session.add(anna)
    await session.flush()  # ensure FK is satisfied before child records

    lab = EHRRecord(
        patient_id="PT0282",
        record_type="lab_panel",
        recorded_at=datetime.datetime(2025, 12, 1, 8, 0, 0),
        payload={"total_cholesterol_mmol": 7.05, "ldl_mmol": 3.84},
        source="test",
    )
    session.add(lab)

    condition = EHRRecord(
        patient_id="PT0282",
        record_type="condition",
        recorded_at=datetime.datetime(2024, 6, 1, 0, 0, 0),
        payload={"icd_code": "E78.0", "description": "Pure hypercholesterolaemia"},
        source="test",
    )
    session.add(condition)

    for i in range(3):
        day = WearableDay(
            patient_id="PT0282",
            date=datetime.date(2025, 12, 7) - datetime.timedelta(days=i),
            resting_hr_bpm=62.0,
            steps=7000,
            sleep_duration_hrs=7.0,
            sleep_quality_score=75,
        )
        session.add(day)

    lp = LifestyleProfile(
        patient_id="PT0282",
        survey_date=datetime.date(2025, 11, 1),
        diet_quality_score=7,
        exercise_sessions_weekly=3,
        stress_level=4,
    )
    session.add(lp)

    await session.flush()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_gdpr_export_bundles_all_data(
    gdpr_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GDPR export must bundle patient profile, EHR records, and wearable data."""
    await _seed_anna_full(db_session)

    resp = await gdpr_client.get("/patients/PT0282/gdpr/export", headers=HEADERS)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["patient_id"] == "PT0282"

    # Patient profile is present.
    assert data["patient"]["name"] == "Anna Weber"
    assert data["patient"]["patient_id"] == "PT0282"

    # EHR records: lab_panel + condition = 2.
    assert len(data["records"]) == 2
    record_types = {r["record_type"] for r in data["records"]}
    assert "lab_panel" in record_types
    assert "condition" in record_types

    # Wearable data: 3 days seeded.
    assert len(data["wearable"]) == 3

    # exported_at must be present.
    assert "exported_at" in data


async def test_gdpr_delete_wellness_framed_ack(
    gdpr_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """DELETE /gdpr must return status='scheduled' with wellness-framed message."""
    await _seed_anna_full(db_session)

    resp = await gdpr_client.delete("/patients/PT0282/gdpr/", headers=HEADERS)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "scheduled"
    assert "wellness" in data["message"].lower() or "data" in data["message"].lower()
    # Specific message per spec.
    assert data["message"] == "Your wellness data will be removed."


async def test_gdpr_export_404_for_unknown_patient(
    gdpr_client: AsyncClient,
) -> None:
    """Export for an unknown patient must return 404."""
    resp = await gdpr_client.get("/patients/PT9999/gdpr/export", headers=HEADERS)
    assert resp.status_code == 404


async def test_gdpr_delete_404_for_unknown_patient(
    gdpr_client: AsyncClient,
) -> None:
    """Delete for an unknown patient must return 404."""
    resp = await gdpr_client.delete("/patients/PT9999/gdpr/", headers=HEADERS)
    assert resp.status_code == 404


async def test_gdpr_export_requires_api_key(
    gdpr_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GDPR export must reject requests without X-API-Key."""
    await _seed_anna_full(db_session)

    resp = await gdpr_client.get("/patients/PT0282/gdpr/export")
    assert resp.status_code == 401


async def test_gdpr_delete_requires_api_key(
    gdpr_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GDPR delete must reject requests without X-API-Key."""
    await _seed_anna_full(db_session)

    resp = await gdpr_client.delete("/patients/PT0282/gdpr/")
    assert resp.status_code == 401


async def test_gdpr_export_isolation_cross_patient(
    gdpr_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Requesting PT0001's GDPR export when only PT0282 exists must return 404."""
    await _seed_anna_full(db_session)

    resp = await gdpr_client.get("/patients/PT0001/gdpr/export", headers=HEADERS)
    assert resp.status_code == 404
