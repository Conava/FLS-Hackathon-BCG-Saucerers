"""Meal log router — multipart photo upload + history.

Endpoints
---------
POST /patients/{patient_id}/meal-log
    Accepts ``multipart/form-data`` with ``image: UploadFile`` and optional
    ``notes: str``.  Delegates to ``MealVisionService.analyze_and_log`` which
    stores the photo via ``PhotoStorage`` and calls ``LLMProvider.generate_vision``.
    Returns ``MealLogUploadResponse`` (MealAnalysis + log_id + photo_uri +
    disclaimer + ai_meta).  HTTP 201 on success.

GET /patients/{patient_id}/meal-log?limit=20
    Returns the most recent meal log entries for the patient via
    ``MealLogRepository.list_recent``.  Returns ``MealLogListOut``.

Both endpoints:
- Require ``X-API-Key`` authentication via ``api_key_auth``.
- Scope every DB access to ``patient_id`` at the SQL level.
- Carry a wellness disclaimer on AI outputs.
- Log only non-PHI fields (patient_id, model, prompt_name, photo_uri prefix).

Stack: FastAPI + SQLModel + SQLAlchemy 2.0 async + Pydantic v2 + google-genai.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.photo_storage import PhotoStorage, get_photo_storage
from app.ai.llm import get_llm_provider
from app.core.config import Settings
from app.core.security import api_key_auth
from app.db.session import get_session
from app.models.meal_log import MealLog
from app.repositories.meal_log_repo import MealLogRepository
from app.schemas.ai_common import AI_DISCLAIMER, AIMeta
from app.schemas.meal_log import MealAnalysis, MealLogListOut, MealLogOut, MealLogUploadResponse
from app.services.meal_vision import MealVisionService

router = APIRouter(prefix="/patients", tags=["meal-log"])


# ---------------------------------------------------------------------------
# Internal helper: reconstruct MealAnalysis from persisted MealLog row
# ---------------------------------------------------------------------------


def _analysis_from_row(row: MealLog) -> MealAnalysis:
    """Reconstruct a ``MealAnalysis`` from a persisted ``MealLog`` row.

    ``MealVisionService`` stores the analysis in two columns:
    - ``macros`` (JSONB): flat dict with ``classification``, macro keys, and
      ``swap_rationale``.
    - ``longevity_swap`` (text): the one-line swap suggestion.

    This helper re-assembles the nested ``MealAnalysis`` schema for the read
    path so the API response matches the upload response schema.

    Args:
        row: A persisted ``MealLog`` instance.

    Returns:
        A validated ``MealAnalysis`` instance.
    """
    macros_raw: dict = row.macros or {}
    # Extract nested macros dict — exclude non-macro keys
    nested_macros = {
        k: macros_raw[k]
        for k in ("kcal", "protein_g", "carbs_g", "fat_g", "fiber_g")
        if k in macros_raw
    }
    return MealAnalysis(
        classification=macros_raw.get("classification", ""),
        macros=nested_macros,
        longevity_swap=row.longevity_swap or "",
        swap_rationale=macros_raw.get("swap_rationale", ""),
    )

# Type aliases
_Session = Annotated[AsyncSession, Depends(get_session)]
_Auth = Annotated[None, Depends(api_key_auth)]


# ---------------------------------------------------------------------------
# Dependency: MealVisionService
# ---------------------------------------------------------------------------


async def get_meal_vision_service(
    session: _Session,
) -> AsyncIterator[MealVisionService]:
    """FastAPI dependency that yields a ``MealVisionService``.

    Wires ``LocalFsPhotoStorage`` (or GCS in prod) and the configured
    ``LLMProvider`` (``FakeLLMProvider`` when ``LLM_PROVIDER=fake``).

    Injected via ``Depends`` so tests can override it cleanly.
    """
    settings = Settings()
    storage: PhotoStorage = get_photo_storage(settings)
    llm = get_llm_provider(settings)
    svc = MealVisionService(session=session, photo_storage=storage, llm=llm)
    yield svc


_MealVisionDep = Annotated[MealVisionService, Depends(get_meal_vision_service)]


# ---------------------------------------------------------------------------
# POST /v1/patients/{patient_id}/meal-log
# ---------------------------------------------------------------------------


@router.post(
    "/{patient_id}/meal-log",
    response_model=MealLogUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a meal photo for analysis and logging",
    tags=["meal-log"],
)
async def upload_meal_log(
    patient_id: str,
    image: UploadFile,
    _auth: _Auth,
    svc: _MealVisionDep,
    notes: str | None = Form(default=None),
) -> MealLogUploadResponse:
    """Accept a multipart photo upload, analyse it with Gemini Vision, and persist.

    Pipeline:
    1. Read the raw image bytes from the ``UploadFile``.
    2. Delegate to ``MealVisionService.analyze_and_log`` which:
       a. Stores the photo via ``PhotoStorage`` → returns a URI.
       b. Calls ``LLMProvider.generate_vision`` → returns ``MealAnalysis``.
       c. Persists a ``MealLog`` row.
    3. Build and return ``MealLogUploadResponse``.

    Args:
        patient_id: Path parameter identifying the patient.
        image:      The uploaded image (JPEG or PNG).
        _auth:      ``api_key_auth`` result (validates ``X-API-Key`` header).
        svc:        Injected ``MealVisionService`` (overridable in tests).
        notes:      Optional free-text notes from the patient.

    Returns:
        ``MealLogUploadResponse`` with HTTP 201.
    """
    image_bytes = await image.read()
    filename = image.filename or "meal.jpg"

    meal_log, analysis = await svc.analyze_and_log(
        patient_id=patient_id,
        image_bytes=image_bytes,
        filename=filename,
        notes=notes,
    )

    ai_meta = AIMeta(
        model="gemini-2.5-flash",
        prompt_name="meal-vision.system",
        request_id=str(uuid.uuid4()),
        token_in=0,
        token_out=0,
        latency_ms=0,
    )

    return MealLogUploadResponse(
        meal_log_id=meal_log.id,  # type: ignore[arg-type]
        photo_uri=meal_log.photo_uri,
        analysis=analysis,
        disclaimer=AI_DISCLAIMER,
        ai_meta=ai_meta,
    )


# ---------------------------------------------------------------------------
# GET /v1/patients/{patient_id}/meal-log
# ---------------------------------------------------------------------------


@router.get(
    "/{patient_id}/meal-log",
    response_model=MealLogListOut,
    status_code=status.HTTP_200_OK,
    summary="Retrieve meal log history for a patient",
    tags=["meal-log"],
)
async def get_meal_log_history(
    patient_id: str,
    session: _Session,
    _auth: _Auth,
    limit: int = Query(default=20, ge=1, le=100),
) -> MealLogListOut:
    """Return the most recent meal log entries for a patient.

    Results are ordered by ``analyzed_at DESC`` (most recent first).
    The response carries up to ``limit`` entries (default 20).

    Args:
        patient_id: Path parameter identifying the patient.
        session:    Injected ``AsyncSession``.
        _auth:      ``api_key_auth`` result.
        limit:      Maximum number of entries to return (1–100, default 20).

    Returns:
        ``MealLogListOut`` with patient_id and a list of ``MealLogOut`` entries.
    """
    repo = MealLogRepository(session)
    rows = await repo.list_recent(patient_id=patient_id, limit=limit)

    log_outs = [
        MealLogOut(
            id=row.id,  # type: ignore[arg-type]
            patient_id=row.patient_id,
            logged_at=row.analyzed_at,
            photo_uri=row.photo_uri,
            analysis=_analysis_from_row(row),
            notes=None,
        )
        for row in rows
    ]

    return MealLogListOut(patient_id=patient_id, logs=log_outs)
