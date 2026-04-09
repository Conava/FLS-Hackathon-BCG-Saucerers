"""Integration tests for the /patients/* endpoints.

Uses a local mini-app-factory fixture (``patients_client``) so this test
module is independent of T16 (main.py).  The fixture overrides ``get_session``
with the testcontainers-backed ``db_session``.

Seeded data:
  - PT0282 (Anna Weber): the primary patient used in most assertions.
  - PT0001 (secondary patient): used to verify cross-patient isolation.

All tests assume ``asyncio_mode = "auto"`` (configured in pyproject.toml).
"""

from __future__ import annotations

import datetime
import os

import pytest
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
async def patients_client(db_session: AsyncSession) -> AsyncClient:  # type: ignore[return]
    """Build a minimal FastAPI app and wrap it in an httpx.AsyncClient.

    ``get_session`` is overridden to yield the test ``db_session`` so every
    HTTP call participates in the per-test transaction (rolled back after each
    test by the root conftest).
    """
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
# DB seed helpers
# ---------------------------------------------------------------------------


async def _seed_anna(session: AsyncSession) -> None:
    """Insert PT0282 (Anna Weber) with a lab panel and 7 wearable days."""
    import datetime

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
        height_cm=165.0,
        weight_kg=68.0,
        bmi=24.98,
        smoking_status="never",
        alcohol_units_weekly=3.0,
    )
    session.add(anna)
    await session.flush()  # ensure FK constraint is satisfied before child records

    # Lab panel with Anna's lipid values.
    lab = EHRRecord(
        patient_id="PT0282",
        record_type="lab_panel",
        recorded_at=datetime.datetime(2025, 12, 1, 8, 0, 0),
        payload={
            "total_cholesterol_mmol": 7.05,
            "ldl_mmol": 3.84,
            "hdl_mmol": 1.2,
            "triglycerides_mmol": 1.8,
            "hba1c_pct": 5.4,
            "fasting_glucose_mmol": 5.2,
            "crp_mg_l": 1.1,
            "egfr_ml_min": 90.0,
            "sbp_mmhg": 122.0,
            "dbp_mmhg": 78.0,
        },
        source="test",
    )
    session.add(lab)

    # Condition record for Anna.
    condition = EHRRecord(
        patient_id="PT0282",
        record_type="condition",
        recorded_at=datetime.datetime(2024, 6, 1, 0, 0, 0),
        payload={"icd_code": "E78.0", "description": "Pure hypercholesterolaemia"},
        source="test",
    )
    session.add(condition)

    # 7 wearable days (most recent first by date, descending).
    base_date = datetime.date(2025, 12, 7)
    for i in range(7):
        day = WearableDay(
            patient_id="PT0282",
            date=base_date - datetime.timedelta(days=i),
            resting_hr_bpm=62.0,
            hrv_rmssd_ms=45.0,
            steps=7200,
            active_minutes=25,
            sleep_duration_hrs=7.0,
            sleep_quality_score=75,
            deep_sleep_pct=22.0,
            spo2_avg_pct=97.5,
            calories_burned_kcal=2100.0,
        )
        session.add(day)

    # Lifestyle profile.
    lp = LifestyleProfile(
        patient_id="PT0282",
        survey_date=datetime.date(2025, 11, 1),
        smoking_status="never",
        alcohol_units_weekly=3.0,
        diet_quality_score=7,
        fruit_veg_servings_daily=4.0,
        meal_frequency_daily=3,
        water_glasses_daily=8,
        exercise_sessions_weekly=3,
        sedentary_hrs_day=5.0,
        stress_level=4,
        sleep_satisfaction=7,
        mental_wellbeing_who5=72,
        self_rated_health=7,
    )
    session.add(lp)

    await session.flush()


async def _seed_secondary(session: AsyncSession) -> None:
    """Insert PT0001 (secondary patient for isolation checks)."""
    import datetime

    from app.models.ehr_record import EHRRecord
    from app.models.patient import Patient

    patient = Patient(
        patient_id="PT0001",
        name="Max Mustermann",
        age=50,
        sex="male",
        country="Germany",
    )
    session.add(patient)
    await session.flush()  # flush patient before adding FK-referencing records

    record = EHRRecord(
        patient_id="PT0001",
        record_type="condition",
        recorded_at=datetime.datetime(2024, 3, 15, 0, 0, 0),
        payload={"icd_code": "I10", "description": "Essential hypertension"},
        source="test",
    )
    session.add(record)
    await session.flush()


# ---------------------------------------------------------------------------
# Health check — no auth required
# ---------------------------------------------------------------------------


async def test_healthz_returns_200_no_auth(patients_client: AsyncClient) -> None:
    """GET /healthz must return 200 without any auth header."""
    resp = await patients_client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Auth enforcement — every non-health route returns 401 without X-API-Key
# ---------------------------------------------------------------------------


async def test_patient_routes_require_api_key(
    patients_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Non-health routes must reject requests without X-API-Key with 401."""
    await _seed_anna(db_session)

    routes = [
        "/patients/PT0282",
        "/patients/PT0282/vitality",
        "/patients/PT0282/records",
        "/patients/PT0282/records/1",
        "/patients/PT0282/wearable",
        "/patients/PT0282/insights",
        "/patients/PT0282/appointments/",
        "/patients/PT0282/gdpr/export",
    ]
    for route in routes:
        resp = await patients_client.get(route)
        assert resp.status_code == 401, f"Expected 401 for {route}, got {resp.status_code}"


# ---------------------------------------------------------------------------
# GET /{patient_id} — profile
# ---------------------------------------------------------------------------


async def test_get_patient_profile_returns_pt0282_as_anna(
    patients_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """PT0282 profile must return Anna Weber's name and demographics."""
    await _seed_anna(db_session)

    resp = await patients_client.get("/patients/PT0282", headers=HEADERS)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["patient_id"] == "PT0282"
    assert data["name"] == "Anna Weber"
    assert data["age"] == 45
    assert data["country"] == "Germany"


async def test_get_patient_profile_404_on_missing(
    patients_client: AsyncClient,
) -> None:
    """Requesting an unknown patient_id must return 404."""
    resp = await patients_client.get("/patients/PT9999", headers=HEADERS)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /{patient_id}/vitality
# ---------------------------------------------------------------------------


async def test_get_vitality_returns_score_subscores_7day_trend_disclaimer(
    patients_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Vitality response must include score, 5 subscores, 7-day trend, disclaimer."""
    await _seed_anna(db_session)

    resp = await patients_client.get("/patients/PT0282/vitality", headers=HEADERS)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Score in valid range.
    assert 0 <= data["score"] <= 100

    # Five expected subscore domains.
    subscores = data["subscores"]
    for key in ("sleep", "activity", "metabolic", "cardio", "lifestyle"):
        assert key in subscores, f"Missing subscore: {key}"
        assert 0 <= subscores[key] <= 100

    # Trend should have <= 7 points (7 wearable days seeded).
    assert len(data["trend"]) <= 7
    assert len(data["trend"]) > 0

    # Disclaimer must be present.
    assert data["disclaimer"] == "Wellness signal, not medical advice."

    # risk_flags is a list.
    assert isinstance(data["risk_flags"], list)


# ---------------------------------------------------------------------------
# GET /{patient_id}/records
# ---------------------------------------------------------------------------


async def test_get_records_lab_panel_returns_anna_lipids_exact(
    patients_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Lab panel payload must have total_cholesterol_mmol=7.05, ldl_mmol=3.84."""
    await _seed_anna(db_session)

    resp = await patients_client.get(
        "/patients/PT0282/records",
        headers=HEADERS,
        params={"type": "lab_panel"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["patient_id"] == "PT0282"
    assert len(data["records"]) == 1

    payload = data["records"][0]["payload"]
    assert payload["total_cholesterol_mmol"] == pytest.approx(7.05, abs=0.01)
    assert payload["ldl_mmol"] == pytest.approx(3.84, abs=0.01)


async def test_get_records_no_filter_returns_all(
    patients_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Without a type filter, all record types are returned."""
    await _seed_anna(db_session)

    resp = await patients_client.get("/patients/PT0282/records", headers=HEADERS)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # 1 lab_panel + 1 condition seeded.
    assert data["total"] == 2


# ---------------------------------------------------------------------------
# GET /{patient_id}/records/{record_id} — cross-patient isolation
# ---------------------------------------------------------------------------


async def test_get_single_record_by_id_404_on_wrong_patient(
    patients_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Fetching PT0001's record via PT0282's path must return 404."""
    await _seed_anna(db_session)
    await _seed_secondary(db_session)

    # Fetch PT0001's records to get a real record_id.
    resp_list = await patients_client.get("/patients/PT0001/records", headers=HEADERS)
    assert resp_list.status_code == 200
    records = resp_list.json()["records"]
    assert len(records) > 0
    pt0001_record_id = records[0]["id"]

    # Attempt to access that record via PT0282's path → 404.
    resp = await patients_client.get(
        f"/patients/PT0282/records/{pt0001_record_id}",
        headers=HEADERS,
    )
    assert resp.status_code == 404, resp.text


async def test_get_single_record_by_id_returns_correct_record(
    patients_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Fetching a valid record through the correct patient path returns 200."""
    await _seed_anna(db_session)

    resp_list = await patients_client.get(
        "/patients/PT0282/records",
        headers=HEADERS,
        params={"type": "lab_panel"},
    )
    assert resp_list.status_code == 200
    lab_id = resp_list.json()["records"][0]["id"]

    resp = await patients_client.get(
        f"/patients/PT0282/records/{lab_id}",
        headers=HEADERS,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["record_type"] == "lab_panel"


# ---------------------------------------------------------------------------
# GET /{patient_id}/wearable
# ---------------------------------------------------------------------------


async def test_get_wearable_last_7_days_returns_ordered_desc(
    patients_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Wearable series must be ordered descending by date (newest first)."""
    await _seed_anna(db_session)

    resp = await patients_client.get(
        "/patients/PT0282/wearable",
        headers=HEADERS,
        params={"days": 7},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["patient_id"] == "PT0282"
    days = data["days"]
    assert len(days) == 7

    # Verify descending order.
    dates = [d["date"] for d in days]
    assert dates == sorted(dates, reverse=True)


# ---------------------------------------------------------------------------
# GET /{patient_id}/insights
# ---------------------------------------------------------------------------


async def test_get_insights_cardio_for_anna(
    patients_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Anna's lipid values trigger at least one cardiovascular insight."""
    await _seed_anna(db_session)

    resp = await patients_client.get("/patients/PT0282/insights", headers=HEADERS)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["patient_id"] == "PT0282"

    # At least one insight should be cardiovascular (elevated LDL=3.84).
    kinds = [i["kind"] for i in data["insights"]]
    assert "cardiovascular" in kinds, f"Expected cardiovascular insight, got: {kinds}"

    # risk_flags should include lipid flag.
    assert "lipid_ldl_elevated" in data["risk_flags"]

    # All insights carry a disclaimer.
    for insight in data["insights"]:
        assert insight["disclaimer"] == "Wellness signal, not medical advice."
