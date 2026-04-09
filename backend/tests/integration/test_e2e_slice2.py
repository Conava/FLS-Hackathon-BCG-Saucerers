"""Slice 2 End-to-End feature test suite.

Five complete user-journey scenarios against a real Testcontainers Postgres +
pgvector database with FakeLLMProvider — no mocks except the LLM provider.

Architecture notes
------------------
* Uses the full ``create_app()`` factory so the real OpenAPI schema is
  exercised and all routers are mounted under ``/v1``.
* ``get_session`` is overridden to yield a session from the committed-data
  engine (same pattern as test_e2e_feature.py).
* Patient IDs use distinct prefixes (``PT_E2E_*``) to avoid collisions with
  the existing Slice 1 E2E fixture data.
* The ``LocalFsPhotoStorage`` injected into the meal-vision service writes to
  a module-scoped temporary directory so photo-file assertions work across
  scenario 4 and 5.
* Each scenario class uses its own patient IDs so concurrent pytest-xdist
  workers cannot collide (though the default runner is single-process).

PHI policy: no patient names, IDs, or clinical values appear in log lines.
Assertions use only synthetic test values seeded here.

Stack: FastAPI + SQLModel + SQLAlchemy 2.0 async + Pydantic v2 + FakeLLMProvider.
"""

from __future__ import annotations

import datetime
import json
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

# ---------------------------------------------------------------------------
# Environment bootstrap — must happen before app.main is imported so Settings
# picks up the correct API_KEY and DATABASE_URL from the test environment.
# ---------------------------------------------------------------------------
os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://ignored")

# ---------------------------------------------------------------------------
# Side-effect imports — register all models for SQLModel metadata
# ---------------------------------------------------------------------------
import app.models  # noqa: F401 — registers all tables

HEADERS = {"X-API-Key": "test-key"}

# Minimal valid 1×1 PNG (67 bytes) — same as test_routers_meal_log.py.
# PNG signature + IHDR + IDAT + IEND chunks.
_MINIMAL_PNG: bytes = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01"
    b"\x00\x00\x00\x01"
    b"\x08\x02"
    b"\x00\x00\x00"
    b"\x90wS\xde"
    b"\x00\x00\x00\x0cIDAT"
    b"x\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
    b"\x00\x00\x00\x00IEND"
    b"\xaeB`\x82"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime.datetime:
    """Return current UTC time as a naive datetime (asyncpg-safe)."""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


def _make_patient(patient_id: str, name: str = "Test E2E Patient") -> app.models.Patient:  # type: ignore[name-defined]
    """Return a minimal Patient row."""
    return app.models.Patient(  # type: ignore[attr-defined]
        patient_id=patient_id,
        name=name,
        age=42,
        sex="female",
        country="DE",
    )


def _parse_sse_events(raw_text: str) -> list[dict[str, Any]]:
    """Parse a raw SSE response body into a list of event data dicts.

    Handles the wire format emitted by sse_starlette::

        event: token
        data: {"type": "token", "text": "chunk"}

    Returns only parsed ``data:`` JSON objects; ``event:`` lines are ignored.
    """
    events: list[dict[str, Any]] = []
    current_data: str | None = None

    for line in raw_text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            current_data = line[len("data:"):].strip()
        elif line == "" and current_data is not None:
            try:
                events.append(json.loads(current_data))
            except json.JSONDecodeError:
                pass
            current_data = None

    # Handle final event without trailing blank line
    if current_data is not None:
        try:
            events.append(json.loads(current_data))
        except json.JSONDecodeError:
            pass

    return events


# ---------------------------------------------------------------------------
# Module-scoped photo storage directory
# ---------------------------------------------------------------------------

# This must be created at module level so both scenario 4 (upload) and
# scenario 5 (delete) share the same storage root.  A module-scoped
# pytest tmp_path is not directly available outside fixtures, so we use
# a Path in the OS temp directory.  It is created in the fixture below.
_PHOTOS_DIR: Path | None = None


@pytest_asyncio.fixture(scope="module", loop_scope="session", autouse=True)
async def _init_photos_dir(tmp_path_factory) -> None:  # type: ignore[no-untyped-def]
    """Create the module-scoped photos directory shared by scenarios 4 and 5."""
    global _PHOTOS_DIR
    _PHOTOS_DIR = tmp_path_factory.mktemp("e2e_slice2_photos")


# ---------------------------------------------------------------------------
# Module-scoped committed-data engine
#
# We use a module-scoped engine that commits data so all scenario classes in
# this module see each other's writes.  Each scenario class manages its own
# patient IDs to avoid cross-test interference.
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module", loop_scope="session")
async def e2e_engine(engine: AsyncEngine) -> AsyncIterator[AsyncEngine]:
    """Yield the shared session-scoped engine for committed E2E writes.

    Unlike the ``db_session`` fixture (which rolls back after every test),
    E2E scenarios commit data so that multi-step journeys across separate
    test methods share the same DB state.

    Teardown: deletes ALL rows seeded by this module after all tests complete
    so the shared Postgres container stays clean for other test modules.
    Other test modules use per-test rollback (``db_session``) and expect an
    empty DB (i.e., committed rows from our E2E tests would corrupt their
    count assertions).
    """
    yield engine

    # ---------------------------------------------------------------------------
    # Teardown — remove all rows committed by this module.
    # Delete in FK-safe order: children before parents.
    # ProtocolAction links through protocol_id (no direct patient_id), so we
    # first collect protocol IDs for E2E patients, then delete actions by those.
    # ---------------------------------------------------------------------------
    from sqlalchemy import delete as sa_delete, select as sa_select

    from app.models.clinical_review import ClinicalReview
    from app.models.daily_log import DailyLog
    from app.models.ehr_record import EHRRecord
    from app.models.lifestyle_profile import LifestyleProfile
    from app.models.meal_log import MealLog
    from app.models.message import Message
    from app.models.notification import Notification
    from app.models.patient import Patient
    from app.models.protocol import Protocol, ProtocolAction
    from app.models.referral import Referral
    from app.models.survey_response import SurveyResponse
    from app.models.vitality_outlook import VitalityOutlook
    from app.models.vitality_snapshot import VitalitySnapshot
    from app.models.wearable_day import WearableDay

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        # Find all protocol IDs belonging to E2E patients
        protocol_result = await session.execute(
            sa_select(Protocol.id).where(
                getattr(Protocol, "patient_id").like("PT_E2E_%")  # type: ignore[arg-type]
            )
        )
        protocol_ids = [row[0] for row in protocol_result.fetchall()]

        # Delete ProtocolAction rows first (FK to Protocol — no patient_id column)
        if protocol_ids:
            await session.execute(
                sa_delete(ProtocolAction).where(
                    getattr(ProtocolAction, "protocol_id").in_(protocol_ids)  # type: ignore[arg-type]
                )
            )

        # Delete all tables with a direct patient_id FK to Patient (children first)
        for model in (
            VitalityOutlook,
            VitalitySnapshot,
            WearableDay,
            MealLog,
            SurveyResponse,
            DailyLog,
            ClinicalReview,
            Message,
            Notification,
            Referral,
            Protocol,
            EHRRecord,
            LifestyleProfile,
        ):
            await session.execute(
                sa_delete(model).where(
                    getattr(model, "patient_id").like("PT_E2E_%")  # type: ignore[arg-type]
                )
            )

        # Delete Patient rows last (all other FKs have been removed above)
        await session.execute(
            sa_delete(Patient).where(
                getattr(Patient, "patient_id").like("PT_E2E_%")  # type: ignore[arg-type]
            )
        )
        await session.commit()


@pytest_asyncio.fixture(scope="module", loop_scope="session")
async def e2e_client(
    e2e_engine: AsyncEngine,
    _init_photos_dir: None,
) -> AsyncIterator[AsyncClient]:
    """Yield an httpx.AsyncClient wired to the full FastAPI app.

    The real ``create_app()`` is used so every router, middleware, and
    OpenAPI schema path is exercised.

    ``get_session`` is overridden to yield a fresh committed session per
    request (not the rollback fixture).  ``get_meal_vision_service`` is
    overridden to inject ``LocalFsPhotoStorage`` backed by ``_PHOTOS_DIR``
    so photo-file assertions work across scenarios.

    Design note: the meal-vision service override takes NO parameters and
    closes over the engine factory + photos_dir.  This matches the pattern
    from test_routers_meal_log.py.  A parameterised override (session: AsyncSession)
    causes FastAPI to interpret the parameter as a query-string field, which
    raises FastAPIError at dependency resolution time.
    """
    from unittest.mock import AsyncMock

    from app.adapters.photo_storage import LocalFsPhotoStorage
    from app.ai.llm import FakeLLMProvider
    from app.db.session import get_session
    from app.main import create_app
    from app.routers import gdpr as gdpr_router
    from app.routers import insights_ai as insights_ai_router
    from app.routers import meal_log as meal_log_router
    from app.routers import protocol as protocol_router
    from app.services.meal_vision import MealVisionService

    assert _PHOTOS_DIR is not None, "_init_photos_dir must run first"
    photos_dir = _PHOTOS_DIR

    app = create_app()
    factory = async_sessionmaker(e2e_engine, expire_on_commit=False)

    async def _fresh_session() -> AsyncIterator[AsyncSession]:
        """Yield a session that auto-commits on clean exit.

        Unlike the rollback fixture (``db_session``), this session commits so
        that writes from one HTTP request are visible to the next request's
        fresh session.  This is required for multi-step E2E journeys where
        routers don't always call ``session.commit()`` themselves.
        """
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # ---------------------------------------------------------------------------
    # Protocol LLM override — FakeLLMProvider with a mocked generate that returns
    # a valid GeneratedProtocol dict (schema has required fields so the base
    # FakeLLMProvider._fake_dict_for_schema returns {} and fails validation).
    # ---------------------------------------------------------------------------
    def _make_generated_protocol_dict(num_actions: int = 3) -> dict:
        """Return a valid GeneratedProtocol-shaped dict."""
        return {
            "rationale": "E2E test protocol — weekly movement focus.",
            "actions": [
                {
                    "category": "movement",
                    "title": f"E2E Action {i + 1}",
                    "target": "15 min",
                    "rationale": f"E2E rationale {i + 1}",
                    "dimension": "cardio_fitness",
                }
                for i in range(num_actions)
            ],
        }

    fake_llm_protocol = FakeLLMProvider()
    fake_llm_protocol.generate = AsyncMock(  # type: ignore[method-assign]
        return_value=_make_generated_protocol_dict(num_actions=3)
    )

    app.dependency_overrides[protocol_router.get_llm] = lambda: fake_llm_protocol

    # ---------------------------------------------------------------------------
    # Insights AI LLM override — same FakeLLMProvider instance for narrator /
    # future-self endpoints.  The base FakeLLMProvider.generate works for these
    # since they don't use response_schema.
    # ---------------------------------------------------------------------------
    fake_llm_insights = FakeLLMProvider()
    app.dependency_overrides[insights_ai_router.get_llm] = lambda: fake_llm_insights

    # ---------------------------------------------------------------------------
    # Meal vision override — no parameters; closes over factory + photos_dir.
    # Must NOT declare a session parameter (FastAPI would interpret it as a
    # query-string field, raising FastAPIError at dependency resolution time).
    # ---------------------------------------------------------------------------
    async def _override_meal_vision() -> AsyncIterator[MealVisionService]:  # type: ignore[return]
        """Yield a MealVisionService backed by LocalFsPhotoStorage + FakeLLMProvider.

        The session auto-commits on clean exit so the MealLog row is visible
        to subsequent requests (e.g., GET /meal-log history).
        """
        async with factory() as session:
            try:
                storage = LocalFsPhotoStorage(base_dir=photos_dir)
                llm = FakeLLMProvider()
                yield MealVisionService(session=session, photo_storage=storage, llm=llm)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # ---------------------------------------------------------------------------
    # GDPR photo storage override — inject the same LocalFsPhotoStorage so the
    # GDPR delete endpoint removes photos from _PHOTOS_DIR (not ./var/photos).
    # ---------------------------------------------------------------------------
    def _override_gdpr_photo_storage() -> LocalFsPhotoStorage:
        return LocalFsPhotoStorage(base_dir=photos_dir)

    app.dependency_overrides[get_session] = _fresh_session
    app.dependency_overrides[
        meal_log_router.get_meal_vision_service
    ] = _override_meal_vision
    app.dependency_overrides[
        gdpr_router.get_photo_storage_dep
    ] = _override_gdpr_photo_storage

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Shared seed helpers
# ---------------------------------------------------------------------------


async def _seed_patient_with_lifestyle(
    factory: async_sessionmaker,
    patient_id: str,
    name: str = "E2E Test Patient",
    time_budget: int = 60,
) -> None:
    """Persist a Patient + LifestyleProfile and commit."""
    from app.models.lifestyle_profile import LifestyleProfile
    from app.models.patient import Patient

    async with factory() as session:
        patient = Patient(
            patient_id=patient_id,
            name=name,
            age=40,
            sex="female",
            country="DE",
        )
        session.add(patient)
        await session.flush()

        lp = LifestyleProfile(
            patient_id=patient_id,
            survey_date=datetime.date(2026, 4, 9),
            diet_quality_score=7,
            time_budget_minutes_per_day=time_budget,
        )
        session.add(lp)
        await session.commit()


async def _seed_patient_only(
    factory: async_sessionmaker,
    patient_id: str,
    name: str = "E2E Patient",
) -> None:
    """Persist a minimal Patient row and commit."""
    from app.models.patient import Patient

    async with factory() as session:
        patient = Patient(
            patient_id=patient_id,
            name=name,
            age=38,
            sex="male",
            country="DE",
        )
        session.add(patient)
        await session.commit()


async def _seed_ehr_record(
    factory: async_sessionmaker,
    patient_id: str,
    record_type: str,
    payload: dict,
) -> int:
    """Persist an EHR record with a fake embedding and return its id."""
    import hashlib
    import random

    from app.models.ehr_record import EHRRecord

    # Generate a deterministic 768-d embedding so the RAG cosine query works.
    h = int(hashlib.md5(f"{patient_id}{record_type}".encode()).hexdigest(), 16)
    rng = random.Random(h)
    embedding = [rng.uniform(-1.0, 1.0) for _ in range(768)]

    async with factory() as session:
        record = EHRRecord(
            patient_id=patient_id,
            record_type=record_type,
            recorded_at=_utcnow(),
            payload=payload,
            source="test",
            embedding=embedding,
        )
        session.add(record)
        await session.flush()
        record_id: int = record.id  # type: ignore[assignment]
        await session.commit()
    return record_id


# ---------------------------------------------------------------------------
# Scenario 1 — Onboarding → Score → Outlook → Protocol → Action complete
#              → Outlook refreshed
# ---------------------------------------------------------------------------


class TestScenario1OnboardingToProtocol:
    """Complete wellness journey: survey → vitality → outlook → protocol → complete → outlook refreshed."""

    _PID = "PT_E2E_S1_JOURNEY"

    async def test_onboarding_survey_accepted(
        self,
        e2e_client: AsyncClient,
        e2e_engine: AsyncEngine,
    ) -> None:
        """POST /v1/patients/{pid}/survey (kind=onboarding) → 201 with SurveyResponseOut."""
        factory = async_sessionmaker(e2e_engine, expire_on_commit=False)
        await _seed_patient_only(factory, self._PID, "Scenario One Patient")

        resp = await e2e_client.post(
            f"/v1/patients/{self._PID}/survey",
            headers=HEADERS,
            json={
                "kind": "onboarding",
                "answers": {
                    "time_budget_minutes_per_day": 45,
                    "diet_quality_score": 6,
                    "exercise_sessions_weekly": 3,
                    "stress_level": 4,
                    "sleep_satisfaction": 7,
                },
            },
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["kind"] == "onboarding"
        assert body["patient_id"] == self._PID
        assert "id" in body
        assert "submitted_at" in body

    async def test_vitality_score_returns_200(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """GET /v1/patients/{pid}/vitality → 200 with score + subscores.

        Patient has no wearable data so the endpoint should return defaults.
        We assert shape only — not exact values.
        """
        resp = await e2e_client.get(
            f"/v1/patients/{self._PID}/vitality",
            headers=HEADERS,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert "score" in body
        assert 0 <= body["score"] <= 100
        assert "disclaimer" in body

    async def test_outlook_initial_returns_three_horizons(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """GET /v1/patients/{pid}/outlook → list of OutlookOut (3, 6, 12 months)."""
        resp = await e2e_client.get(
            f"/v1/patients/{self._PID}/outlook",
            headers=HEADERS,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 3
        horizons = {item["horizon_months"] for item in body}
        assert horizons == {3, 6, 12}

    async def test_protocol_generate_returns_actions(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """POST /v1/patients/{pid}/protocol/generate → ProtocolOut with actions."""
        resp = await e2e_client.post(
            f"/v1/patients/{self._PID}/protocol/generate",
            headers=HEADERS,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["patient_id"] == self._PID
        assert "id" in body
        assert isinstance(body["actions"], list)
        assert len(body["actions"]) >= 1

    async def test_complete_action_updates_streak(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """POST /v1/patients/{pid}/protocol/complete-action → streak incremented."""
        # Fetch the active protocol to get an action_id
        get_resp = await e2e_client.get(
            f"/v1/patients/{self._PID}/protocol",
            headers=HEADERS,
        )
        assert get_resp.status_code == 200, get_resp.text
        actions = get_resp.json()["actions"]
        assert len(actions) >= 1, "Expected at least one action to complete"
        action_id = actions[0]["id"]

        resp = await e2e_client.post(
            f"/v1/patients/{self._PID}/protocol/complete-action",
            headers=HEADERS,
            json={"action_id": action_id},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["action_id"] == action_id
        assert body["streak_days"] == 1
        assert "completed_at" in body

    async def test_outlook_refreshed_after_action_complete(
        self,
        e2e_client: AsyncClient,
        e2e_engine: AsyncEngine,
    ) -> None:
        """GET /v1/patients/{pid}/outlook after completing an action shows updated outlook.

        After complete-action the protocol router recomputes and upserts
        VitalityOutlook rows.  We assert that rows still exist for all three
        horizons and that projected_score is a valid float in [0, 100].
        """
        resp = await e2e_client.get(
            f"/v1/patients/{self._PID}/outlook",
            headers=HEADERS,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 3
        for item in body:
            assert 0 <= item["projected_score"] <= 100, (
                f"projected_score out of range: {item['projected_score']}"
            )
        horizons = {item["horizon_months"] for item in body}
        assert horizons == {3, 6, 12}, f"Unexpected horizons: {horizons}"


# ---------------------------------------------------------------------------
# Scenario 2 — Records Q&A with citations + cross-patient isolation
# ---------------------------------------------------------------------------


class TestScenario2RecordsQACitations:
    """RAG Q&A: patient A gets citations from their own records only; B's data absent."""

    _PID_A = "PT_E2E_S2_RAG_A"
    _PID_B = "PT_E2E_S2_RAG_B"

    async def test_seed_two_patients_with_ehr(
        self,
        e2e_engine: AsyncEngine,
    ) -> None:
        """Seed patients A and B with distinguishable EHR records."""
        factory = async_sessionmaker(e2e_engine, expire_on_commit=False)
        await _seed_patient_only(factory, self._PID_A, "RAG Patient Alpha")
        await _seed_patient_only(factory, self._PID_B, "RAG Patient Beta")

        # Patient A — a lab_panel record with a cholesterol reading
        await _seed_ehr_record(
            factory,
            patient_id=self._PID_A,
            record_type="lab_panel",
            payload={
                "total_cholesterol_mmol": 6.5,
                "ldl_mmol": 3.2,
                "hdl_mmol": 1.4,
                "triglycerides_mmol": 1.1,
                "hba1c_pct": 5.4,
                "fasting_glucose_mmol": 5.0,
                "crp_mg_l": 0.8,
                "egfr_ml_min": 90,
                "sbp_mmhg": 120,
                "dbp_mmhg": 78,
            },
        )

        # Patient B — a condition record with sentinel value
        await _seed_ehr_record(
            factory,
            patient_id=self._PID_B,
            record_type="condition",
            payload={
                "icd_code": "Z99.9",
                "description": "PATIENT_B_SENTINEL_CONDITION_XYZ999",
            },
        )

    async def test_qa_returns_answer_with_citations(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """POST /v1/patients/A/records/qa → answer with citations from A's records."""
        resp = await e2e_client.post(
            f"/v1/patients/{self._PID_A}/records/qa",
            headers=HEADERS,
            json={"question": "What are my cholesterol levels?"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert "answer" in body
        assert isinstance(body["answer"], str)
        assert len(body["answer"]) > 0
        assert "disclaimer" in body
        assert isinstance(body["citations"], list)
        assert len(body["citations"]) >= 1, (
            f"Expected at least one citation from patient A's records, got: {body['citations']}"
        )

    async def test_citations_scoped_to_patient_a_only(
        self,
        e2e_client: AsyncClient,
        e2e_engine: AsyncEngine,
    ) -> None:
        """All citations in A's Q&A response must reference A's record IDs only.

        Retrieves patient B's record IDs from the DB and asserts none appear
        in patient A's citations — the SQL isolation guarantee.
        """
        from sqlalchemy import select

        from app.models.ehr_record import EHRRecord

        factory = async_sessionmaker(e2e_engine, expire_on_commit=False)
        async with factory() as session:
            pid_attr = getattr(EHRRecord, "patient_id")
            result = await session.execute(
                select(EHRRecord.id).where(pid_attr == self._PID_B)
            )
            b_record_ids = {row[0] for row in result.fetchall()}

        # Ask question as patient A
        resp = await e2e_client.post(
            f"/v1/patients/{self._PID_A}/records/qa",
            headers=HEADERS,
            json={"question": "Tell me about my health records."},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()

        # No citation record_id from patient B must appear in A's response
        cited_ids = {c["record_id"] for c in body.get("citations", [])}
        leaked = cited_ids & b_record_ids
        assert not leaked, (
            f"Cross-patient isolation failure: patient B's record IDs {leaked} "
            f"appeared in patient A's Q&A citations"
        )

        # The answer text must not contain patient B's sentinel
        answer_text = body.get("answer", "")
        assert "PATIENT_B_SENTINEL_CONDITION_XYZ999" not in answer_text, (
            "Patient B's sentinel condition description leaked into patient A's answer"
        )


# ---------------------------------------------------------------------------
# Scenario 3 — Coach SSE streaming: token events + done event + disclaimer
# ---------------------------------------------------------------------------


class TestScenario3CoachStreaming:
    """Coach SSE stream yields token events, a done event, and a wellness disclaimer."""

    _PID = "PT_E2E_S3_COACH"

    async def test_seed_patient(
        self,
        e2e_engine: AsyncEngine,
    ) -> None:
        """Seed the coach-scenario patient."""
        factory = async_sessionmaker(e2e_engine, expire_on_commit=False)
        await _seed_patient_only(factory, self._PID, "Coach E2E Patient")

    async def test_coach_chat_yields_token_events(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """POST /v1/patients/{pid}/coach/chat → SSE stream with >=1 token events."""
        resp = await e2e_client.post(
            f"/v1/patients/{self._PID}/coach/chat",
            headers=HEADERS,
            json={"message": "How can I improve my sleep?", "history": []},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert "text/event-stream" in resp.headers.get("content-type", ""), (
            f"Expected SSE content-type, got: {resp.headers.get('content-type')}"
        )

        events = _parse_sse_events(resp.text)
        token_events = [e for e in events if e.get("type") == "token"]
        assert len(token_events) >= 1, (
            f"Expected >=1 token events, got event types: {[e.get('type') for e in events]}"
        )

    async def test_coach_chat_done_event_has_disclaimer(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """The final done event must carry a non-empty wellness disclaimer."""
        resp = await e2e_client.post(
            f"/v1/patients/{self._PID}/coach/chat",
            headers=HEADERS,
            json={"message": "What foods should I eat for longevity?", "history": []},
        )
        assert resp.status_code == 200, resp.text

        events = _parse_sse_events(resp.text)

        # done must be the last event
        assert len(events) > 0, "No SSE events received"
        assert events[-1].get("type") == "done", (
            f"Expected last event to be 'done', got: {events[-1].get('type')}"
        )

        done_event = events[-1]
        disclaimer = done_event.get("disclaimer", "")
        assert isinstance(disclaimer, str) and len(disclaimer) > 0, (
            f"done event missing disclaimer field: {done_event}"
        )
        # Wellness framing: must mention medical advice
        assert "medical advice" in disclaimer.lower() or "not medical" in disclaimer.lower(), (
            f"Disclaimer does not contain wellness framing: {disclaimer!r}"
        )

    async def test_coach_chat_done_event_has_ai_meta(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """The done event must carry ai_meta with model and prompt_name."""
        resp = await e2e_client.post(
            f"/v1/patients/{self._PID}/coach/chat",
            headers=HEADERS,
            json={"message": "Summarise my health journey.", "history": []},
        )
        assert resp.status_code == 200, resp.text

        events = _parse_sse_events(resp.text)
        done = next((e for e in events if e.get("type") == "done"), None)
        assert done is not None, "No done event in SSE stream"

        ai_meta = done.get("ai_meta")
        assert isinstance(ai_meta, dict), f"ai_meta is not a dict: {ai_meta!r}"
        assert "model" in ai_meta, f"ai_meta missing 'model': {ai_meta}"
        assert "prompt_name" in ai_meta, f"ai_meta missing 'prompt_name': {ai_meta}"


# ---------------------------------------------------------------------------
# Scenario 4 — Meal photo upload → MealLog persisted → appears in history
# ---------------------------------------------------------------------------


class TestScenario4MealPhotoUpload:
    """Meal photo upload creates a MealLog row, stores a photo file, and appears in GET history."""

    _PID = "PT_E2E_S4_MEAL"

    async def test_seed_patient(
        self,
        e2e_engine: AsyncEngine,
    ) -> None:
        """Seed the meal-scenario patient."""
        factory = async_sessionmaker(e2e_engine, expire_on_commit=False)
        await _seed_patient_only(factory, self._PID, "Meal E2E Patient")

    async def test_meal_upload_returns_201_with_analysis_and_uri(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """POST /v1/patients/{pid}/meal-log → 201 with MealAnalysis + photo_uri."""
        resp = await e2e_client.post(
            f"/v1/patients/{self._PID}/meal-log",
            headers=HEADERS,
            files={"image": ("dinner.png", _MINIMAL_PNG, "image/png")},
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

        body = resp.json()
        assert isinstance(body["meal_log_id"], int)
        assert isinstance(body["photo_uri"], str)
        assert body["photo_uri"].startswith("file://"), (
            f"Expected file:// URI from local storage, got: {body['photo_uri']!r}"
        )

        # File must actually exist on disk
        photo_path = Path(body["photo_uri"][len("file://"):])
        assert photo_path.exists(), f"Photo file not found on disk: {photo_path}"
        assert photo_path.read_bytes() == _MINIMAL_PNG

        # MealAnalysis shape
        analysis = body["analysis"]
        assert analysis["classification"], "classification must be non-empty"
        assert "macros" in analysis
        assert "longevity_swap" in analysis

        # AI envelope
        assert body["disclaimer"], "disclaimer must be non-empty"
        assert "ai_meta" in body

    async def test_meal_log_appears_in_history(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """GET /v1/patients/{pid}/meal-log → list includes the uploaded meal."""
        resp = await e2e_client.get(
            f"/v1/patients/{self._PID}/meal-log",
            headers=HEADERS,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["patient_id"] == self._PID
        logs = body["logs"]
        assert len(logs) >= 1, (
            f"Expected >=1 meal log entries in history after upload, got: {logs}"
        )

        # Each log entry has the expected shape
        log = logs[0]
        assert "id" in log
        assert "photo_uri" in log
        assert "analysis" in log

    async def test_meal_log_photo_uri_persisted_in_db(
        self,
        e2e_client: AsyncClient,
        e2e_engine: AsyncEngine,
    ) -> None:
        """The persisted MealLog row in the DB has a non-null photo_uri.

        Verifies that the photo URI is stored at the DB level (not just
        returned in the HTTP response).
        """
        from sqlalchemy import select

        from app.models.meal_log import MealLog

        factory = async_sessionmaker(e2e_engine, expire_on_commit=False)
        async with factory() as session:
            pid_attr = getattr(MealLog, "patient_id")
            result = await session.execute(
                select(MealLog).where(pid_attr == self._PID)
            )
            rows = list(result.scalars().all())

        assert len(rows) >= 1, f"Expected >=1 MealLog DB row for {self._PID}"
        for row in rows:
            assert row.photo_uri is not None, "photo_uri must not be None in the DB row"
            assert row.photo_uri.startswith("file://"), (
                f"Expected file:// URI in DB, got: {row.photo_uri!r}"
            )


# ---------------------------------------------------------------------------
# Scenario 5 — GDPR delete-my-data removes MealLog rows AND photo files
# ---------------------------------------------------------------------------


class TestScenario5GDPRDeleteRemovesPhotos:
    """GDPR delete endpoint must purge all MealLog rows and photo files for the patient.

    This scenario verifies the fix added to backend/app/routers/gdpr.py:
    the DELETE handler now calls MealLogRepository.delete_for_patient() and
    photo_storage.delete_all_for_patient() in addition to the existing Patient
    deletion stub.

    The scenario:
    1. Upload a meal photo for patient GDPR_A.
    2. Assert the MealLog row exists and the file is on disk.
    3. Call DELETE /v1/patients/GDPR_A/gdpr/.
    4. Assert:
       a. Response is 200 with status='scheduled'.
       b. All MealLog rows for GDPR_A are gone from the DB.
       c. The photo file is no longer on disk.
    """

    _PID = "PT_E2E_S5_GDPR"

    async def test_seed_patient(
        self,
        e2e_engine: AsyncEngine,
    ) -> None:
        """Seed the GDPR-scenario patient."""
        factory = async_sessionmaker(e2e_engine, expire_on_commit=False)
        await _seed_patient_only(factory, self._PID, "GDPR Delete E2E Patient")

    async def test_upload_meal_photo_for_gdpr_patient(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """Upload a meal photo so there is something for GDPR to delete."""
        resp = await e2e_client.post(
            f"/v1/patients/{self._PID}/meal-log",
            headers=HEADERS,
            files={"image": ("lunch.png", _MINIMAL_PNG, "image/png")},
        )
        assert resp.status_code == 201, f"Upload failed: {resp.text}"

        body = resp.json()
        photo_uri = body["photo_uri"]
        assert photo_uri.startswith("file://")

        # Confirm the file exists at this point
        photo_path = Path(photo_uri[len("file://"):])
        assert photo_path.exists(), f"Photo must exist before GDPR delete: {photo_path}"

    async def test_meal_log_and_photo_exist_before_delete(
        self,
        e2e_engine: AsyncEngine,
    ) -> None:
        """Assert MealLog row exists in DB and photo file is on disk pre-delete."""
        from sqlalchemy import select

        from app.models.meal_log import MealLog

        factory = async_sessionmaker(e2e_engine, expire_on_commit=False)
        async with factory() as session:
            pid_attr = getattr(MealLog, "patient_id")
            result = await session.execute(
                select(MealLog).where(pid_attr == self._PID)
            )
            rows = list(result.scalars().all())

        assert len(rows) >= 1, (
            f"Expected >=1 MealLog row for {self._PID} before GDPR delete"
        )

        # Verify each row's photo file exists
        for row in rows:
            assert row.photo_uri is not None
            photo_path = Path(row.photo_uri[len("file://"):])
            assert photo_path.exists(), (
                f"Photo file must exist before GDPR delete: {photo_path}"
            )

    async def test_gdpr_delete_returns_scheduled(
        self,
        e2e_client: AsyncClient,
    ) -> None:
        """DELETE /v1/patients/{pid}/gdpr/ → 200 with status='scheduled'."""
        resp = await e2e_client.delete(
            f"/v1/patients/{self._PID}/gdpr/",
            headers=HEADERS,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["status"] == "scheduled", (
            f"Expected status='scheduled', got: {body['status']!r}"
        )
        assert "message" in body

    async def test_meal_log_rows_deleted_after_gdpr(
        self,
        e2e_engine: AsyncEngine,
    ) -> None:
        """All MealLog rows for the patient are absent after GDPR delete."""
        from sqlalchemy import select

        from app.models.meal_log import MealLog

        factory = async_sessionmaker(e2e_engine, expire_on_commit=False)
        async with factory() as session:
            pid_attr = getattr(MealLog, "patient_id")
            result = await session.execute(
                select(MealLog).where(pid_attr == self._PID)
            )
            rows = list(result.scalars().all())

        assert rows == [], (
            f"Expected 0 MealLog rows after GDPR delete, found {len(rows)} rows for "
            f"{self._PID}: {[r.id for r in rows]}"
        )

    async def test_photo_files_deleted_after_gdpr(
        self,
        e2e_engine: AsyncEngine,
    ) -> None:
        """All photo files for the patient are removed from disk after GDPR delete.

        Checks the photos directory for any files under the patient's sub-directory.
        """
        assert _PHOTOS_DIR is not None, "Photos directory not initialised"

        patient_dir = _PHOTOS_DIR / self._PID
        if patient_dir.exists():
            remaining = list(patient_dir.iterdir())
            assert remaining == [], (
                f"Expected photo directory to be empty after GDPR delete, "
                f"found: {[str(p) for p in remaining]}"
            )
        # If the directory itself was removed (LocalFsPhotoStorage.delete_all_for_patient
        # removes the dir when empty), that is also acceptable.
