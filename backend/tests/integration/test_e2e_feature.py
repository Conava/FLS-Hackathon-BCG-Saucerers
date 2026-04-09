"""End-to-end feature tests — five critical demo paths.

These tests exercise the full stack through real HTTP endpoints against a
testcontainers Postgres database, with real CSV ingestion, real repositories,
real vitality engine, and real router logic.  No mocks.

Critical paths
--------------
1. Happy path — Anna's dashboard (PT0282): ingest → GET profile/vitality/
   records/insights/wearable/appointments → assert correct values.
2. Ingest idempotency: run ingest twice → row counts unchanged, responses
   stable.
3. Cross-patient isolation: PT0001 record via PT0282 path → 404; no data
   leakage across patient boundaries.
4. Auth enforcement: missing/wrong X-API-Key → 401 on every protected route.
5. GDPR stubs: export returns full bundle; delete returns wellness-framed ack.

Architecture notes
------------------
* ``ingest_session`` (module-scoped) runs ingest once at module load and owns
  its own connection, separate from the per-test ``db_session``.  Data is
  committed into the shared testcontainers Postgres and is visible to all
  subsequent tests.
* Each test creates its own ``app_client`` wired to a fresh ``AsyncSession``
  that reads the committed data without touching the ingest session.
* ``db_session`` (per-test rollback from conftest) is NOT used here because
  ``UnifiedProfileService.ingest()`` calls ``session.commit()``.  Using the
  rollback session would leave data in an inconsistent state after the outer
  rollback.

PHI policy: no patient names, IDs, or clinical values appear in log lines.
Test assertions use exact values from ``tests/fixtures/ehr_sample.csv``.
"""

from __future__ import annotations

import os
import re
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

# ---------------------------------------------------------------------------
# Environment bootstrap — must happen before app.main is imported so Settings
# picks up the correct API_KEY and DATABASE_URL from the test environment.
# ---------------------------------------------------------------------------

os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://ignored")

# ---------------------------------------------------------------------------
# Side-effect imports — register the CSV adapter in the adapter registry
# ---------------------------------------------------------------------------

import app.adapters.csv_source  # noqa: F401  # registers @register("csv")
from app.models import EHRRecord, LifestyleProfile, Patient, WearableDay  # noqa: E402
from app.models.vitality_snapshot import VitalitySnapshot  # noqa: E402
from app.services.unified_profile import UnifiedProfileService  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HEADERS = {"X-API-Key": "test-key"}
WRONG_HEADERS = {"X-API-Key": "wrong"}
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

# Routes that require auth (excludes /healthz)
PROTECTED_ROUTES = [
    "/v1/patients/PT0282",
    "/v1/patients/PT0282/vitality",
    "/v1/patients/PT0282/records",
    "/v1/patients/PT0282/wearable",
    "/v1/patients/PT0282/insights",
    "/v1/patients/PT0282/appointments/",
    "/v1/patients/PT0282/gdpr/export",
]

PROTECTED_DELETE_ROUTES: list[str] = ["/v1/patients/PT0282/gdpr/"]


# ---------------------------------------------------------------------------
# Module-scoped ingest fixture
#
# Runs ingest once per module into the shared Postgres container.  Data persists
# across all tests in this module (no rollback).  Uses a dedicated session
# separate from the per-test ``db_session`` to avoid interfering with the
# rollback fixture.
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module", loop_scope="session")
async def ingested_engine(engine: AsyncEngine) -> AsyncIterator[AsyncEngine]:
    """Run CSV ingest once for this module, then yield the engine.

    Data is committed into the real Postgres schema (created by the session-
    scoped ``engine`` fixture in conftest).  All tests in this module read
    committed data, so they share the same Postgres state.

    Teardown: all ingested data is deleted after the module finishes so the
    shared Postgres container remains clean for other test modules (the T14
    router tests use ``db_session`` rollback fixtures that expect an empty DB).

    Yields the same ``engine`` object so downstream fixtures can open their own
    sessions against it.
    """
    from sqlalchemy import delete as sa_delete

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        svc = UnifiedProfileService(session)
        await svc.ingest("csv", data_dir=FIXTURES_DIR)
        # Final commit is called inside ingest(), but make sure no pending work.
        await session.commit()

    yield engine

    # ---------------------------------------------------------------------------
    # Teardown — remove all ingested rows so other test modules start clean.
    # Delete in FK-safe order: children before parents.
    # ---------------------------------------------------------------------------
    async with factory() as session:
        # Delete in FK-safe order: snapshot and children before Patient.
        for model in (VitalitySnapshot, EHRRecord, WearableDay, LifestyleProfile, Patient):
            await session.execute(sa_delete(model))
        await session.commit()


@pytest_asyncio.fixture(loop_scope="session")
async def e2e_client(ingested_engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    """Yield an httpx.AsyncClient backed by the full FastAPI app.

    ``get_session`` is overridden to yield a fresh session against the
    ``ingested_engine`` (which has real committed data from ingest).  Each test
    gets a fresh session so that session state does not leak between tests.
    """
    from app.db.session import get_session
    from app.main import create_app

    app = create_app()
    factory = async_sessionmaker(ingested_engine, expire_on_commit=False)

    async def _fresh_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = _fresh_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Scenario 1 — Happy path: Anna's full dashboard (PT0282)
# ---------------------------------------------------------------------------


class TestAnnaDashboard:
    """Scenario 1: every endpoint returns correct data for Anna (PT0282)."""

    async def test_get_patient_profile_returns_anna(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """GET /patients/PT0282 → 200 with Anna in the name."""
        resp = await e2e_client.get("/v1/patients/PT0282", headers=HEADERS)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "Anna" in data["name"], f"Expected 'Anna' in name, got: {data['name']}"
        assert data["patient_id"] == "PT0282"

    async def test_get_vitality_score_and_subscores(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """GET /patients/PT0282/vitality → score in [0,100], 5 subscores, trend, disclaimer."""
        resp = await e2e_client.get("/v1/patients/PT0282/vitality", headers=HEADERS)
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Composite score must be in valid range.
        assert 0 <= data["score"] <= 100, f"Score out of range: {data['score']}"

        # All five domain subscores must be present and in range.
        subscores = data["subscores"]
        for key in ("sleep", "activity", "metabolic", "cardio", "lifestyle"):
            assert key in subscores, f"Missing subscore: {key}"
            assert 0 <= subscores[key] <= 100, f"Subscore {key} out of range: {subscores[key]}"

        # Trend: up to 7 points (PT0282 has 90 wearable days, but request defaults to 7).
        assert 0 < len(data["trend"]) <= 7, f"Unexpected trend length: {len(data['trend'])}"

        # Disclaimer is mandatory.
        assert data["disclaimer"] == "Wellness signal, not medical advice."

    async def test_get_records_lab_panel_exact_lipid_values(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """GET /patients/PT0282/records?type=lab_panel → exact cholesterol values."""
        resp = await e2e_client.get(
            "/v1/patients/PT0282/records",
            headers=HEADERS,
            params={"type": "lab_panel"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        records = data["records"]
        assert len(records) >= 1, "Expected at least one lab_panel record for PT0282"

        # The fixture CSV has total_cholesterol_mmol=7.05, ldl_mmol=3.84 for PT0282.
        payload = records[0]["payload"]
        assert payload["total_cholesterol_mmol"] == pytest.approx(7.05, abs=0.01), (
            f"total_cholesterol_mmol: expected 7.05, got {payload['total_cholesterol_mmol']}"
        )
        assert payload["ldl_mmol"] == pytest.approx(3.84, abs=0.01), (
            f"ldl_mmol: expected 3.84, got {payload['ldl_mmol']}"
        )

    async def test_get_insights_cardiovascular_with_lipid_signal(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """GET /patients/PT0282/insights → cardiovascular insight with lipid signal."""
        resp = await e2e_client.get("/v1/patients/PT0282/insights", headers=HEADERS)
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # At least one cardiovascular insight must be present (LDL=3.84 > 3.0 threshold).
        kinds = [i["kind"] for i in data["insights"]]
        assert "cardiovascular" in kinds, (
            f"Expected cardiovascular insight for Anna (LDL=3.84), got: {kinds}"
        )

        # The cardiovascular insight must reference the lipid signal.
        cardio_insight = next(i for i in data["insights"] if i["kind"] == "cardiovascular")
        signals_text = " ".join(cardio_insight["signals"]).lower()
        assert any(
            kw in signals_text for kw in ("ldl", "cholesterol", "lipid")
        ), f"No lipid keyword found in signals: {cardio_insight['signals']}"

    async def test_get_wearable_days_returned(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """GET /patients/PT0282/wearable?days=7 → non-empty list (up to 7 days)."""
        resp = await e2e_client.get(
            "/v1/patients/PT0282/wearable",
            headers=HEADERS,
            params={"days": 7},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["patient_id"] == "PT0282"
        # PT0282 has 90 wearable days in fixtures; requesting 7 should return up to 7.
        days = data["days"]
        assert 0 < len(days) <= 7, f"Expected 1–7 wearable days, got {len(days)}"

    async def test_get_appointments_at_least_two_for_anna(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """GET /patients/PT0282/appointments/ → at least 2 appointments for Anna."""
        resp = await e2e_client.get("/v1/patients/PT0282/appointments/", headers=HEADERS)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["patient_id"] == "PT0282"
        # Anna (PT0282) gets ≥ 2 appointments from the static stub (T15).
        assert len(data["appointments"]) >= 2, (
            f"Expected ≥ 2 appointments for PT0282, got {len(data['appointments'])}"
        )


# ---------------------------------------------------------------------------
# Scenario 2 — Ingest idempotency
# ---------------------------------------------------------------------------


class TestIngestIdempotency:
    """Scenario 2: running ingest twice leaves row counts unchanged."""

    async def test_row_counts_stable_after_second_ingest(
        self,
        ingested_engine: AsyncEngine,
    ) -> None:
        """Two ingest runs must produce identical row counts for all tables."""
        factory = async_sessionmaker(ingested_engine, expire_on_commit=False)

        # Count rows after the first ingest (already done by ingested_engine fixture).
        async with factory() as session:
            counts_after_run1: dict[str, int] = {}
            for model in (Patient, EHRRecord, WearableDay, LifestyleProfile):
                result = await session.execute(
                    select(func.count()).select_from(model)
                )
                counts_after_run1[model.__tablename__] = result.scalar_one()  # type: ignore[attr-defined]

        # Run ingest a second time.
        async with factory() as session:
            svc = UnifiedProfileService(session)
            await svc.ingest("csv", data_dir=FIXTURES_DIR)
            await session.commit()

        # Count rows after the second ingest.
        async with factory() as session:
            counts_after_run2: dict[str, int] = {}
            for model in (Patient, EHRRecord, WearableDay, LifestyleProfile):
                result = await session.execute(
                    select(func.count()).select_from(model)
                )
                counts_after_run2[model.__tablename__] = result.scalar_one()  # type: ignore[attr-defined]

        # Every table's row count must be identical.
        assert counts_after_run1 == counts_after_run2, (
            f"Idempotency broken — counts changed after second ingest:\n"
            f"  run1: {counts_after_run1}\n"
            f"  run2: {counts_after_run2}"
        )
        # Sanity: all counts must be positive (data was actually loaded).
        for table, count in counts_after_run1.items():
            assert count > 0, f"Table {table!r} is empty after ingest"

    async def test_vitality_response_stable_after_second_ingest(
        self,
        e2e_client: AsyncClient,
        ingested_engine: AsyncEngine,
    ) -> None:
        """Vitality score for PT0282 must be the same before and after a second ingest."""
        # Fetch vitality before second ingest (data already ingested by fixture).
        resp1 = await e2e_client.get("/v1/patients/PT0282/vitality", headers=HEADERS)
        assert resp1.status_code == 200, resp1.text
        score_before = resp1.json()["score"]
        subscores_before = resp1.json()["subscores"]

        # Run ingest a second time.
        factory = async_sessionmaker(ingested_engine, expire_on_commit=False)
        async with factory() as session:
            svc = UnifiedProfileService(session)
            await svc.ingest("csv", data_dir=FIXTURES_DIR)
            await session.commit()

        # Fetch vitality after second ingest.
        resp2 = await e2e_client.get("/v1/patients/PT0282/vitality", headers=HEADERS)
        assert resp2.status_code == 200, resp2.text
        score_after = resp2.json()["score"]
        subscores_after = resp2.json()["subscores"]

        # Scores must be identical (same underlying data).
        assert score_before == pytest.approx(score_after, abs=0.01), (
            f"Vitality score changed after second ingest: {score_before} → {score_after}"
        )
        for key in subscores_before:
            assert subscores_before[key] == pytest.approx(subscores_after[key], abs=0.01), (
                f"Subscore '{key}' changed after second ingest"
            )


# ---------------------------------------------------------------------------
# Scenario 3 — Cross-patient isolation (GDPR compliance pitch test)
# ---------------------------------------------------------------------------


class TestCrossPatientIsolation:
    """Scenario 3: no data leakage across patient boundaries."""

    async def test_pt0001_record_via_pt0282_path_returns_404(
        self,
        e2e_client: AsyncClient,
        ingested_engine: AsyncEngine,
    ) -> None:
        """Fetching a PT0001 record via the PT0282 path must return 404."""
        factory = async_sessionmaker(ingested_engine, expire_on_commit=False)
        async with factory() as session:
            result = await session.execute(
                select(EHRRecord.id).where(EHRRecord.patient_id == "PT0001").limit(1)
            )
            pt0001_record_id = result.scalar_one_or_none()

        assert pt0001_record_id is not None, "PT0001 must have EHR records after ingest"

        # The PT0001 record via the PT0282 path must return 404, not 200.
        resp = await e2e_client.get(
            f"/v1/patients/PT0282/records/{pt0001_record_id}",
            headers=HEADERS,
        )
        assert resp.status_code == 404, (
            f"Expected 404 for cross-patient record access, got {resp.status_code}: {resp.text}"
        )

    async def test_all_read_routes_isolate_by_patient(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """Every read route for a non-existent patient returns 404 or empty list.

        Using patient ID 'PT_NONEXISTENT' (not in fixtures) guarantees that no
        real data can be returned — the router must either 404 or return an
        empty payload without leaking any other patient's data.
        """
        ghost_id = "PT_NONEXISTENT"

        # Routes that must return 404 (patient existence check enforced).
        must_404_routes = [
            f"/v1/patients/{ghost_id}",
            f"/v1/patients/{ghost_id}/vitality",
            f"/v1/patients/{ghost_id}/records",
            f"/v1/patients/{ghost_id}/wearable",
            f"/v1/patients/{ghost_id}/insights",
            f"/v1/patients/{ghost_id}/appointments/",
            f"/v1/patients/{ghost_id}/gdpr/export",
        ]
        for route in must_404_routes:
            resp = await e2e_client.get(route, headers=HEADERS)
            assert resp.status_code == 404, (
                f"Expected 404 for {route} (unknown patient), got {resp.status_code}"
            )

    async def test_pt0282_data_not_accessible_via_pt0001_path(
        self,
        e2e_client: AsyncClient,
        ingested_engine: AsyncEngine,
    ) -> None:
        """PT0282's records must not appear when querying through PT0001's path."""
        factory = async_sessionmaker(ingested_engine, expire_on_commit=False)
        async with factory() as session:
            result = await session.execute(
                select(EHRRecord.id).where(EHRRecord.patient_id == "PT0282").limit(1)
            )
            pt0282_record_id = result.scalar_one_or_none()

        assert pt0282_record_id is not None, "PT0282 must have EHR records after ingest"

        # PT0282's record via PT0001 path must return 404.
        resp = await e2e_client.get(
            f"/v1/patients/PT0001/records/{pt0282_record_id}",
            headers=HEADERS,
        )
        assert resp.status_code == 404, (
            f"Expected 404 for cross-patient record access (PT0282→PT0001), "
            f"got {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# Scenario 4 — Auth enforcement
# ---------------------------------------------------------------------------


class TestAuthEnforcement:
    """Scenario 4: every protected route rejects missing or wrong API keys."""

    async def test_healthz_no_auth_returns_200(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """GET /healthz without auth must return 200 (unauthenticated liveness probe)."""
        resp = await e2e_client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_protected_routes_reject_missing_key(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """Every non-health route without X-API-Key must return 401."""
        for route in PROTECTED_ROUTES:
            resp = await e2e_client.get(route)
            assert resp.status_code == 401, (
                f"GET {route} should be 401"
            )
        for route in PROTECTED_DELETE_ROUTES:
            resp = await e2e_client.delete(route)
            assert resp.status_code == 401, (
                f"DELETE {route} should be 401"
            )

    async def test_protected_routes_reject_wrong_key(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """Every non-health route with a wrong X-API-Key must return 401."""
        headers = {"X-API-Key": "wrong-key"}
        for route in PROTECTED_ROUTES:
            resp = await e2e_client.get(route, headers=headers)
            assert resp.status_code == 401
        for route in PROTECTED_DELETE_ROUTES:
            resp = await e2e_client.delete(route, headers=headers)
            assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Scenario 5 — GDPR stubs
# ---------------------------------------------------------------------------


class TestGDPRStubs:
    """Scenario 5: GDPR export and delete endpoints return correct shapes."""

    async def test_gdpr_export_returns_full_bundle(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """GET /patients/PT0282/gdpr/export → 200 with patient/records/wearable/lifestyle."""
        resp = await e2e_client.get("/v1/patients/PT0282/gdpr/export", headers=HEADERS)
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # All four top-level bundle keys must be present.
        for key in ("patient", "records", "wearable", "lifestyle"):
            assert key in data, f"Missing top-level GDPR export key: {key!r}"

        # Patient sub-object must identify PT0282.
        assert data["patient"]["patient_id"] == "PT0282"

        # Records and wearable must be non-empty lists (Anna has lab data + wearable days).
        assert isinstance(data["records"], list), "records must be a list"
        assert len(data["records"]) >= 1, "Expected ≥ 1 EHR record in GDPR export"
        assert isinstance(data["wearable"], list), "wearable must be a list"
        assert len(data["wearable"]) >= 1, "Expected ≥ 1 wearable day in GDPR export"

    async def test_gdpr_delete_ack_status_and_wellness_framing(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """DELETE /patients/PT0282/gdpr/ → 200 with status='scheduled' + wellness message."""
        resp = await e2e_client.delete("/v1/patients/PT0282/gdpr/", headers=HEADERS)
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Status must always be 'scheduled' (async erasure stub).
        assert data["status"] == "scheduled", (
            f"Expected status='scheduled', got {data['status']!r}"
        )

        # Message must be present and wellness-framed (no diagnostic verbs).
        assert "message" in data, "GDPR delete ack missing 'message' field"
        message = data["message"]
        assert message, "GDPR delete ack message must not be empty"

        # Legal requirement: no diagnostic verbs in the message.
        forbidden_pattern = re.compile(
            r"\b(diagnos|treat|cure|disease)\w*", re.IGNORECASE
        )
        matches = forbidden_pattern.findall(message)
        assert not matches, (
            f"Diagnostic verb(s) found in GDPR delete message: {matches}\n"
            f"  message: {message!r}"
        )
