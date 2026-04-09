"""Integration tests for the /v1/patients/{patient_id}/insights/* and /v1/patients/{patient_id}/outlook endpoints.

Uses the mini-app-factory pattern so tests are independent of main.py (T23b
registers routers globally; this test module sets up its own minimal app).

Scenarios covered:
  1. POST /v1/patients/{pid}/insights/outlook-narrator — happy path (disclaimer present).
  2. POST /v1/patients/{pid}/insights/future-self — happy path (disclaimer present).
  3. GET /v1/patients/{pid}/outlook — returns persisted or freshly-computed outlook.
  4. GET /v1/patients/{pid}/outlook — fresh compute when no cached row exists (upserts).
  5. Cross-patient isolation: one patient's insight call never returns the other's data.
  6. 401 returned when API key is missing.
"""

from __future__ import annotations

import datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 — registers all SQLModel tables

HEADERS = {"X-API-Key": "test-key"}


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _dt() -> datetime.datetime:
    """Return a naive UTC datetime."""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


async def _seed_patient(session: AsyncSession, patient_id: str) -> None:
    """Insert a minimal Patient row."""
    p = app.models.Patient(
        patient_id=patient_id,
        name=f"Test {patient_id}",
        age=40,
        sex="unknown",
        country="DE",
        created_at=_dt(),
        updated_at=_dt(),
    )
    session.add(p)
    await session.flush()


async def _seed_vitality_snapshot(
    session: AsyncSession,
    patient_id: str,
    score: float = 68.5,
) -> None:
    """Insert a VitalitySnapshot row (required for compute_outlook current_score lookup)."""
    snap = app.models.VitalitySnapshot(
        patient_id=patient_id,
        computed_at=_dt(),
        score=score,
        subscores={"cardio": 70.0, "sleep": 65.0},
        risk_flags={},
    )
    session.add(snap)
    await session.flush()


async def _seed_outlook(
    session: AsyncSession,
    patient_id: str,
    horizon_months: int = 3,
    projected_score: float = 72.0,
) -> None:
    """Insert a VitalityOutlook row for the given patient."""
    o = app.models.VitalityOutlook(
        patient_id=patient_id,
        horizon_months=horizon_months,
        projected_score=projected_score,
        narrative="Pre-existing narrative",
        computed_at=_dt(),
    )
    session.add(o)
    await session.flush()


# ---------------------------------------------------------------------------
# Mini-app factory fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session")
async def insights_client(db_session: AsyncSession) -> AsyncClient:  # type: ignore[return]
    """Build a minimal FastAPI app with the insights_ai router and a FakeLLMProvider."""
    from fastapi import FastAPI
    from httpx import AsyncClient
    from httpx._transports.asgi import ASGITransport

    from app.ai.llm import FakeLLMProvider
    from app.db.session import get_session
    from app.routers import health
    from app.routers.insights_ai import router as insights_router
    from app.routers.insights_ai import get_llm  # type: ignore[attr-defined]

    app = FastAPI()
    app.include_router(health.router)
    app.include_router(insights_router, prefix="/v1")

    async def _override_session():  # type: ignore[return]
        yield db_session

    def _override_llm() -> FakeLLMProvider:
        return FakeLLMProvider()

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_llm] = _override_llm

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# POST /v1/patients/{pid}/insights/outlook-narrator
# ---------------------------------------------------------------------------


class TestOutlookNarratorEndpoint:
    """Happy-path and auth tests for the Outlook Narrator endpoint."""

    async def test_narrator_returns_200_with_narrative(
        self,
        insights_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """POST outlook-narrator returns 200 with a non-empty narrative."""
        await _seed_patient(db_session, "PT_NAR_R01")
        await _seed_vitality_snapshot(db_session, "PT_NAR_R01")
        # Seed an outlook so the service has something to narrate
        await _seed_outlook(db_session, "PT_NAR_R01", horizon_months=6)

        resp = await insights_client.post(
            "/v1/patients/PT_NAR_R01/insights/outlook-narrator",
            json={
                "patient_id": "PT_NAR_R01",
                "horizon_months": 6,
                "top_drivers": ["sleep", "nutrition"],
            },
            headers=HEADERS,
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body.get("narrative"), "narrative must be a non-empty string"

    async def test_narrator_response_contains_disclaimer(
        self,
        insights_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """POST outlook-narrator response body carries a wellness disclaimer."""
        await _seed_patient(db_session, "PT_NAR_R02")
        await _seed_vitality_snapshot(db_session, "PT_NAR_R02")
        await _seed_outlook(db_session, "PT_NAR_R02", horizon_months=3)

        resp = await insights_client.post(
            "/v1/patients/PT_NAR_R02/insights/outlook-narrator",
            json={"patient_id": "PT_NAR_R02", "horizon_months": 3, "top_drivers": []},
            headers=HEADERS,
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        disclaimer = body.get("disclaimer", "")
        assert disclaimer, "disclaimer field must be present and non-empty"
        # Wellness framing — no diagnostic verbs
        for bad_word in ("diagnose", "treat", "cure", "prevent-disease"):
            assert bad_word.lower() not in disclaimer.lower(), (
                f"Forbidden word '{bad_word}' found in disclaimer"
            )

    async def test_narrator_response_contains_ai_meta(
        self,
        insights_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """POST outlook-narrator response includes ai_meta."""
        await _seed_patient(db_session, "PT_NAR_R03")
        await _seed_vitality_snapshot(db_session, "PT_NAR_R03")
        await _seed_outlook(db_session, "PT_NAR_R03", horizon_months=6)

        resp = await insights_client.post(
            "/v1/patients/PT_NAR_R03/insights/outlook-narrator",
            json={"patient_id": "PT_NAR_R03", "horizon_months": 6, "top_drivers": []},
            headers=HEADERS,
        )

        assert resp.status_code == 200, resp.text
        ai_meta = resp.json().get("ai_meta")
        assert ai_meta is not None, "ai_meta must be present"
        assert ai_meta.get("prompt_name") == "outlook-narrator"
        assert ai_meta.get("model"), "model must be non-empty"
        assert ai_meta.get("request_id"), "request_id must be non-empty"

    async def test_narrator_returns_404_for_unknown_patient(
        self,
        insights_client: AsyncClient,
    ) -> None:
        """POST outlook-narrator returns 404 when patient does not exist."""
        resp = await insights_client.post(
            "/v1/patients/UNKNOWN_PATIENT/insights/outlook-narrator",
            json={
                "patient_id": "UNKNOWN_PATIENT",
                "horizon_months": 6,
                "top_drivers": [],
            },
            headers=HEADERS,
        )

        assert resp.status_code == 404, resp.text

    async def test_narrator_returns_401_without_api_key(
        self,
        insights_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """POST outlook-narrator returns 401 when X-API-Key is absent."""
        await _seed_patient(db_session, "PT_NAR_R04")

        resp = await insights_client.post(
            "/v1/patients/PT_NAR_R04/insights/outlook-narrator",
            json={"patient_id": "PT_NAR_R04", "horizon_months": 3, "top_drivers": []},
        )

        assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# POST /v1/patients/{pid}/insights/future-self
# ---------------------------------------------------------------------------


class TestFutureSelfEndpoint:
    """Happy-path and auth tests for the Future Self endpoint."""

    async def test_future_self_returns_200_with_bio_age(
        self,
        insights_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """POST future-self returns 200 with a non-negative bio_age."""
        await _seed_patient(db_session, "PT_FS_R01")

        resp = await insights_client.post(
            "/v1/patients/PT_FS_R01/insights/future-self",
            json={
                "patient_id": "PT_FS_R01",
                "sliders": {"sleep_improvement": 2, "exercise_frequency": 4},
            },
            headers=HEADERS,
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert isinstance(body.get("bio_age"), int), "bio_age must be an int"
        assert body["bio_age"] >= 0, "bio_age must be non-negative"

    async def test_future_self_response_contains_disclaimer(
        self,
        insights_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """POST future-self response carries a wellness disclaimer."""
        await _seed_patient(db_session, "PT_FS_R02")

        resp = await insights_client.post(
            "/v1/patients/PT_FS_R02/insights/future-self",
            json={"patient_id": "PT_FS_R02", "sliders": {}},
            headers=HEADERS,
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        disclaimer = body.get("disclaimer", "")
        assert disclaimer, "disclaimer field must be present and non-empty"
        for bad_word in ("diagnose", "treat", "cure", "prevent-disease"):
            assert bad_word.lower() not in disclaimer.lower(), (
                f"Forbidden word '{bad_word}' found in disclaimer"
            )

    async def test_future_self_response_contains_ai_meta(
        self,
        insights_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """POST future-self response includes ai_meta with correct prompt_name."""
        await _seed_patient(db_session, "PT_FS_R03")

        resp = await insights_client.post(
            "/v1/patients/PT_FS_R03/insights/future-self",
            json={"patient_id": "PT_FS_R03", "sliders": {"nutrition": 3}},
            headers=HEADERS,
        )

        assert resp.status_code == 200, resp.text
        ai_meta = resp.json().get("ai_meta")
        assert ai_meta is not None, "ai_meta must be present"
        assert ai_meta.get("prompt_name") == "future-self"
        assert ai_meta.get("model"), "model must be non-empty"

    async def test_future_self_returns_401_without_api_key(
        self,
        insights_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """POST future-self returns 401 when X-API-Key is absent."""
        await _seed_patient(db_session, "PT_FS_R04")

        resp = await insights_client.post(
            "/v1/patients/PT_FS_R04/insights/future-self",
            json={"patient_id": "PT_FS_R04", "sliders": {}},
        )

        assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# GET /v1/patients/{pid}/outlook
# ---------------------------------------------------------------------------


class TestGetOutlookEndpoint:
    """Tests for GET /v1/patients/{pid}/outlook."""

    async def test_get_outlook_returns_persisted_row(
        self,
        insights_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """GET outlook returns the latest persisted VitalityOutlook row."""
        await _seed_patient(db_session, "PT_OL_R01")
        await _seed_vitality_snapshot(db_session, "PT_OL_R01", score=72.0)
        await _seed_outlook(db_session, "PT_OL_R01", horizon_months=3, projected_score=74.0)

        resp = await insights_client.get(
            "/v1/patients/PT_OL_R01/outlook",
            headers=HEADERS,
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Should return a list of outlooks (one per horizon)
        assert isinstance(body, list), f"Expected list, got {type(body)}"
        assert len(body) >= 1, "Expected at least one outlook row"
        horizons = [o["horizon_months"] for o in body]
        assert 3 in horizons, f"Expected horizon 3 in {horizons}"

    async def test_get_outlook_computes_fresh_when_no_cache(
        self,
        insights_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """GET outlook computes and upserts a fresh row when no cached row exists."""
        await _seed_patient(db_session, "PT_OL_R02")
        await _seed_vitality_snapshot(db_session, "PT_OL_R02", score=65.0)
        # No VitalityOutlook seeded — should trigger fresh compute + upsert

        resp = await insights_client.get(
            "/v1/patients/PT_OL_R02/outlook",
            headers=HEADERS,
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert isinstance(body, list), f"Expected list, got {type(body)}"
        # compute_outlook returns {3, 6, 12} horizons — all three should be upserted
        horizons = {o["horizon_months"] for o in body}
        assert horizons == {3, 6, 12}, f"Expected {{3,6,12}}, got {horizons}"

    async def test_get_outlook_returns_404_for_unknown_patient(
        self,
        insights_client: AsyncClient,
    ) -> None:
        """GET outlook returns 404 when patient does not exist."""
        resp = await insights_client.get(
            "/v1/patients/UNKNOWN_PATIENT_OL/outlook",
            headers=HEADERS,
        )

        assert resp.status_code == 404, resp.text

    async def test_get_outlook_returns_401_without_api_key(
        self,
        insights_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """GET outlook returns 401 when X-API-Key is absent."""
        await _seed_patient(db_session, "PT_OL_R03")

        resp = await insights_client.get("/v1/patients/PT_OL_R03/outlook")

        assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# Cross-patient isolation
# ---------------------------------------------------------------------------


class TestCrossPatientIsolation:
    """Verify that insights calls for patient A never leak data to patient B."""

    async def test_narrator_isolation(
        self,
        insights_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Narrator for PT_ISO_A does not create or expose PT_ISO_B outlook rows."""
        await _seed_patient(db_session, "PT_ISO_NA")
        await _seed_patient(db_session, "PT_ISO_NB")
        await _seed_vitality_snapshot(db_session, "PT_ISO_NA")
        await _seed_outlook(db_session, "PT_ISO_NA", horizon_months=6)

        # Call narrator for A
        resp_a = await insights_client.post(
            "/v1/patients/PT_ISO_NA/insights/outlook-narrator",
            json={"patient_id": "PT_ISO_NA", "horizon_months": 6, "top_drivers": []},
            headers=HEADERS,
        )
        assert resp_a.status_code == 200, resp_a.text

        # Query outlook for B — should return empty or 404 (no rows)
        from sqlalchemy import select

        from app.models.vitality_outlook import VitalityOutlook

        stmt = select(VitalityOutlook).where(
            getattr(VitalityOutlook, "patient_id") == "PT_ISO_NB"
        )
        result = await db_session.execute(stmt)
        rows = list(result.scalars().all())
        assert len(rows) == 0, f"Expected 0 rows for PT_ISO_NB, got {len(rows)}"

    async def test_outlook_endpoint_isolation(
        self,
        insights_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """GET outlook for PT_ISO_CA returns only PT_ISO_CA's rows."""
        await _seed_patient(db_session, "PT_ISO_CA")
        await _seed_patient(db_session, "PT_ISO_CB")
        await _seed_vitality_snapshot(db_session, "PT_ISO_CA", score=70.0)
        await _seed_vitality_snapshot(db_session, "PT_ISO_CB", score=80.0)
        await _seed_outlook(db_session, "PT_ISO_CA", horizon_months=3, projected_score=71.0)
        await _seed_outlook(db_session, "PT_ISO_CB", horizon_months=3, projected_score=82.0)

        resp = await insights_client.get(
            "/v1/patients/PT_ISO_CA/outlook",
            headers=HEADERS,
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        for outlook_item in body:
            assert outlook_item["projected_score"] != 82.0, (
                "PT_ISO_CB's projected_score (82.0) must not appear in PT_ISO_CA's response"
            )
