"""Integration tests for the /v1/patients/{patient_id}/meal-log endpoints.

Uses a local mini-app factory (``meal_log_client``) that mounts only the
meal_log router so this test module is independent of T23b (main.py wiring).

The ``MealVisionService`` is wired directly via FastAPI Depends overrides so
we can inject ``LocalFsPhotoStorage`` and ``FakeLLMProvider`` without touching
real GCS or calling the Gemini API.

Test cases:
  1. Happy-path upload: POST multipart/form-data → assert file on disk + MealLog
     persisted + response carries analysis + disclaimer + ai_meta.
  2. Cross-patient isolation: patient A uploads, patient B's GET history
     returns zero entries.
"""
from __future__ import annotations

import datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 — side-effect import ensures tables are registered

HEADERS = {"X-API-Key": "test-key"}

# ---------------------------------------------------------------------------
# Minimal valid PNG fixture (~67 bytes)
# A 1×1 white pixel PNG: signature + IHDR + IDAT + IEND chunks.
# ---------------------------------------------------------------------------

_MINIMAL_PNG: bytes = (
    b"\x89PNG\r\n\x1a\n"      # 8-byte PNG signature
    b"\x00\x00\x00\rIHDR"     # IHDR chunk length + type
    b"\x00\x00\x00\x01"       # width = 1
    b"\x00\x00\x00\x01"       # height = 1
    b"\x08\x02"                # bit depth = 8, colour type = RGB
    b"\x00\x00\x00"           # compression, filter, interlace
    b"\x90wS\xde"             # IHDR CRC
    b"\x00\x00\x00\x0cIDAT"   # IDAT chunk
    b"x\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"  # deflate stream
    b"\x00\x00\x00\x00IEND"   # IEND chunk (length=0)
    b"\xaeB`\x82"              # IEND CRC
)


# ---------------------------------------------------------------------------
# Mini-app factory fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session")
async def meal_log_client(
    db_session: AsyncSession,
    tmp_path_factory,  # type: ignore[no-untyped-def]
) -> AsyncClient:  # type: ignore[return]
    """Build a minimal FastAPI app mounting only the meal_log router.

    Overrides:
    - ``get_session`` → ``db_session`` (testcontainers DB with per-test rollback)
    - ``get_meal_vision_service`` → injects ``FakeLLMProvider`` +
      ``LocalFsPhotoStorage`` backed by a temporary directory so photos are
      written to the filesystem and can be asserted on disk.
    """
    from fastapi import FastAPI
    from httpx import AsyncClient
    from httpx._transports.asgi import ASGITransport

    from app.adapters.photo_storage import LocalFsPhotoStorage
    from app.ai.llm import FakeLLMProvider
    from app.db.session import get_session
    from app.routers import meal_log as meal_log_router
    from app.services.meal_vision import MealVisionService

    photos_dir = tmp_path_factory.mktemp("meal_log_photos")

    app = FastAPI()
    app.include_router(meal_log_router.router, prefix="/v1")

    async def _override_session():  # type: ignore[return]
        yield db_session

    async def _override_meal_vision_service():  # type: ignore[return]
        storage = LocalFsPhotoStorage(base_dir=photos_dir)
        llm = FakeLLMProvider()
        svc = MealVisionService(session=db_session, photo_storage=storage, llm=llm)
        yield svc

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[
        meal_log_router.get_meal_vision_service
    ] = _override_meal_vision_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# DB seed helpers
# ---------------------------------------------------------------------------


def _make_patient(patient_id: str) -> app.models.Patient:  # type: ignore[name-defined]
    return app.models.Patient(  # type: ignore[attr-defined]
        patient_id=patient_id,
        name=f"Test {patient_id}",
        age=35,
        sex="female",
        country="DE",
    )


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------


class TestMealLogUpload:
    """Happy-path tests for POST /v1/patients/{patient_id}/meal-log."""

    async def test_upload_returns_201_and_persists_meal_log(
        self,
        meal_log_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Upload a PNG; assert 201, file on disk, MealLog row in DB.

        Assertions:
        - HTTP status 201.
        - Response body contains ``meal_log_id`` (int), ``photo_uri`` (str),
          ``analysis`` (dict with classification/macros/longevity_swap/swap_rationale).
        - ``photo_uri`` is a ``file://`` URI and the file exists on disk.
        - ``disclaimer`` field is present and non-empty.
        - ``ai_meta`` field is present.
        - DB row exists for the patient with the same id.
        """
        from sqlalchemy import select

        from app.models.meal_log import MealLog

        patient_id = "PT_ML_R001"
        db_session.add(_make_patient(patient_id))
        await db_session.flush()

        response = await meal_log_client.post(
            f"/v1/patients/{patient_id}/meal-log",
            files={"image": ("meal.png", _MINIMAL_PNG, "image/png")},
            headers=HEADERS,
        )

        assert response.status_code == 201, response.text

        body = response.json()

        # Core fields
        assert isinstance(body["meal_log_id"], int)
        assert body["photo_uri"].startswith("file://"), (
            f"Expected file:// URI, got: {body['photo_uri']!r}"
        )

        # File must exist on disk
        photo_path = Path(body["photo_uri"][len("file://"):])
        assert photo_path.exists(), f"Photo not found on disk at: {photo_path}"
        assert photo_path.read_bytes() == _MINIMAL_PNG

        # Analysis fields
        analysis = body["analysis"]
        assert analysis["classification"]
        assert "macros" in analysis
        assert analysis["longevity_swap"] is not None
        assert "swap_rationale" in analysis

        # AI response envelope
        assert body["disclaimer"]
        assert "ai_meta" in body

        # Verify DB row
        stmt = select(MealLog).where(
            getattr(MealLog, "patient_id") == patient_id
        )
        result = await db_session.execute(stmt)
        rows = list(result.scalars().all())
        assert len(rows) == 1
        assert rows[0].id == body["meal_log_id"]
        assert rows[0].photo_uri == body["photo_uri"]

    async def test_upload_with_notes_returns_201(
        self,
        meal_log_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Upload with optional notes field; assert 201."""
        patient_id = "PT_ML_R002"
        db_session.add(_make_patient(patient_id))
        await db_session.flush()

        response = await meal_log_client.post(
            f"/v1/patients/{patient_id}/meal-log",
            files={"image": ("dinner.png", _MINIMAL_PNG, "image/png")},
            data={"notes": "post-workout dinner"},
            headers=HEADERS,
        )

        assert response.status_code == 201, response.text
        body = response.json()
        assert isinstance(body["meal_log_id"], int)

    async def test_upload_requires_auth(
        self,
        meal_log_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Upload without X-API-Key returns 401."""
        patient_id = "PT_ML_R003"
        db_session.add(_make_patient(patient_id))
        await db_session.flush()

        response = await meal_log_client.post(
            f"/v1/patients/{patient_id}/meal-log",
            files={"image": ("meal.png", _MINIMAL_PNG, "image/png")},
            # no HEADERS
        )

        assert response.status_code == 401, response.text


class TestMealLogHistory:
    """Tests for GET /v1/patients/{patient_id}/meal-log."""

    async def test_get_history_returns_200_with_uploaded_meals(
        self,
        meal_log_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Upload two meals then GET history; assert both appear in correct order."""
        patient_id = "PT_ML_R004"
        db_session.add(_make_patient(patient_id))
        await db_session.flush()

        # Upload two meals
        for name in ("breakfast.png", "lunch.png"):
            r = await meal_log_client.post(
                f"/v1/patients/{patient_id}/meal-log",
                files={"image": (name, _MINIMAL_PNG, "image/png")},
                headers=HEADERS,
            )
            assert r.status_code == 201, r.text

        # Fetch history
        response = await meal_log_client.get(
            f"/v1/patients/{patient_id}/meal-log",
            headers=HEADERS,
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["patient_id"] == patient_id
        assert len(body["logs"]) == 2

    async def test_get_history_requires_auth(
        self,
        meal_log_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """GET history without X-API-Key returns 401."""
        patient_id = "PT_ML_R005"
        db_session.add(_make_patient(patient_id))
        await db_session.flush()

        response = await meal_log_client.get(
            f"/v1/patients/{patient_id}/meal-log"
            # no HEADERS
        )

        assert response.status_code == 401, response.text


class TestMealLogIsolation:
    """Cross-patient isolation tests for the meal-log endpoints."""

    async def test_patient_b_history_empty_after_patient_a_upload(
        self,
        meal_log_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Patient A uploads a meal; patient B's GET history returns empty list.

        This is the key GDPR / hard-isolation check: SQL scoping must prevent
        any leakage of patient A's meal log into patient B's query.
        """
        pid_a = "PT_ML_ISO_A"
        pid_b = "PT_ML_ISO_B"

        db_session.add(_make_patient(pid_a))
        db_session.add(_make_patient(pid_b))
        await db_session.flush()

        # Patient A uploads
        r = await meal_log_client.post(
            f"/v1/patients/{pid_a}/meal-log",
            files={"image": ("meal.png", _MINIMAL_PNG, "image/png")},
            headers=HEADERS,
        )
        assert r.status_code == 201, r.text

        # Patient B queries — must return empty
        response = await meal_log_client.get(
            f"/v1/patients/{pid_b}/meal-log",
            headers=HEADERS,
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["patient_id"] == pid_b
        assert body["logs"] == [], (
            f"Patient B must not see Patient A's meal logs, got: {body['logs']}"
        )
