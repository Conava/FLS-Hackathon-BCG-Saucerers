"""Insights AI router — LLM-powered Outlook Narrator, Future Self Simulator, and Outlook GET.

Endpoints:
  POST /v1/patients/{patient_id}/insights/outlook-narrator
      → OutlookNarratorService.narrate() → OutlookNarratorResponse

  POST /v1/patients/{patient_id}/insights/future-self
      → FutureSelfService.project() → FutureSelfResponse

  GET /v1/patients/{patient_id}/outlook
      → latest VitalityOutlook rows via VitalityOutlookRepository.latest;
        if no cached row exists, compute fresh via compute_outlook + upsert.
        Returns a list of OutlookOut (one per horizon: 3, 6, 12 months).

Every AI response carries a ``disclaimer`` and ``ai_meta`` (from
``AIResponseEnvelope``).  Every request requires ``X-API-Key`` authentication.

Patient isolation: all queries and service calls flow through patient_id from
the URL path parameter — never from the request body.

Stack: FastAPI + SQLAlchemy 2.0 async + Pydantic v2 (no v1 syntax).

PHI policy: no patient name, email, or PII is logged — only request_id, model,
prompt_name, and latency_ms are emitted in structured log lines.
"""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import FakeLLMProvider, LLMProvider
from app.core.config import Settings
from app.core.security import api_key_auth
from app.db.session import get_session
from app.repositories.outlook_repo import VitalityOutlookRepository
from app.repositories.patient_repo import PatientRepository
from app.repositories.vitality_repo import VitalityRepository
from app.schemas.outlook import (
    FutureSelfRequest,
    FutureSelfResponse,
    OutlookNarratorRequest,
    OutlookNarratorResponse,
    OutlookOut,
)
from app.services.future_self import FutureSelfService
from app.services.outlook_engine import compute_outlook
from app.services.outlook_narrator import OutlookNarratorService

router = APIRouter(prefix="/patients", tags=["insights"])

# Type aliases for dependency injection to keep endpoint signatures concise.
_Session = Annotated[AsyncSession, Depends(get_session)]
_Auth = Annotated[None, Depends(api_key_auth)]

# Horizons for fresh-compute path (months).
_HORIZONS: list[int] = [3, 6, 12]


# ---------------------------------------------------------------------------
# LLM provider dependency
# ---------------------------------------------------------------------------


def get_llm() -> LLMProvider:
    """FastAPI dependency that returns the configured LLMProvider.

    Uses ``FakeLLMProvider`` when ``LLM_PROVIDER=fake`` (the default for dev
    and tests).  ``GeminiProvider`` is returned in production.

    This function is registered as a dependency so tests can override it via
    ``app.dependency_overrides[get_llm] = lambda: FakeLLMProvider()``.
    """
    settings = Settings()
    llm_provider = getattr(settings, "llm_provider", "fake")
    if llm_provider == "gemini":
        from app.ai.llm import GeminiProvider

        return GeminiProvider(
            project=str(settings.gcp_project),
            location=str(getattr(settings, "gcp_location", "europe-west3")),
        )
    return FakeLLMProvider()


_LLM = Annotated[LLMProvider, Depends(get_llm)]


# ---------------------------------------------------------------------------
# Helper: assert patient exists
# ---------------------------------------------------------------------------


async def _require_patient(patient_id: str, session: AsyncSession) -> None:
    """Raise HTTP 404 if the patient does not exist in the database.

    Args:
        patient_id: The patient to check.
        session:    The current AsyncSession.

    Raises:
        HTTPException: 404 Not Found when the patient is absent.
    """
    repo = PatientRepository(session)
    patient = await repo.get(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found.",
        )


# ---------------------------------------------------------------------------
# POST /v1/patients/{patient_id}/insights/outlook-narrator
# ---------------------------------------------------------------------------


@router.post(
    "/{patient_id}/insights/outlook-narrator",
    response_model=OutlookNarratorResponse,
    summary="Generate a one-sentence wellness narrative for the patient's outlook",
    tags=["insights"],
)
async def post_outlook_narrator(
    patient_id: str,
    body: OutlookNarratorRequest,
    session: _Session,
    llm: _LLM,
    _auth: _Auth,
) -> OutlookNarratorResponse:
    """Generate a wellness narrative for the patient's vitality outlook.

    Looks up the latest ``VitalityOutlook`` row for the requested horizon,
    then calls ``OutlookNarratorService.narrate()`` to produce a one-sentence
    AI-generated narrative.  If no outlook row exists for the horizon, the
    endpoint returns HTTP 404 (the caller should first fetch
    ``GET /v1/patients/{pid}/outlook`` to ensure the row is computed).

    Args:
        patient_id: URL path parameter — the patient whose outlook to narrate.
        body:       ``OutlookNarratorRequest`` with ``horizon_months``.
        session:    Injected ``AsyncSession``.
        llm:        Injected ``LLMProvider`` (``FakeLLMProvider`` in tests).
        _auth:      API key authentication guard (result discarded).

    Returns:
        ``OutlookNarratorResponse`` with ``narrative``, ``disclaimer``,
        and ``ai_meta``.
    """
    await _require_patient(patient_id, session)

    outlook_repo = VitalityOutlookRepository(session)
    horizon = body.horizon_months
    outlook = await outlook_repo.latest(patient_id=patient_id, horizon_months=horizon)

    if outlook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No VitalityOutlook found for patient {patient_id!r} "
                f"at horizon {horizon} months. "
                "Call GET /v1/patients/{patient_id}/outlook first to compute it."
            ),
        )

    service = OutlookNarratorService(llm=llm, session=session)
    return await service.narrate(patient_id=patient_id, outlook=outlook)


# ---------------------------------------------------------------------------
# POST /v1/patients/{patient_id}/insights/future-self
# ---------------------------------------------------------------------------


@router.post(
    "/{patient_id}/insights/future-self",
    response_model=FutureSelfResponse,
    summary="Project the patient's future biological age and wellness trajectory",
    tags=["insights"],
)
async def post_future_self(
    patient_id: str,
    body: FutureSelfRequest,
    session: _Session,
    llm: _LLM,
    _auth: _Auth,
) -> FutureSelfResponse:
    """Simulate the patient's future self given lifestyle slider adjustments.

    Calls ``FutureSelfService.project()`` which invokes the ``future-self``
    LLM prompt with the slider values, returning a projected biological age
    and a wellness-framed narrative comparing current vs improved trajectory.

    Args:
        patient_id: URL path parameter — the patient to project.
        body:       ``FutureSelfRequest`` with ``sliders`` dict.
        session:    Injected ``AsyncSession``.
        llm:        Injected ``LLMProvider``.
        _auth:      API key authentication guard.

    Returns:
        ``FutureSelfResponse`` with ``bio_age``, ``narrative``, ``disclaimer``,
        and ``ai_meta``.
    """
    await _require_patient(patient_id, session)

    service = FutureSelfService(llm=llm, session=session)
    return await service.project(patient_id=patient_id, sliders=body.sliders)


# ---------------------------------------------------------------------------
# GET /v1/patients/{patient_id}/outlook
# ---------------------------------------------------------------------------


@router.get(
    "/{patient_id}/outlook",
    response_model=list[OutlookOut],
    summary="Get the patient's vitality outlook projections (3, 6, 12 months)",
    tags=["insights"],
)
async def get_outlook(
    patient_id: str,
    session: _Session,
    _auth: _Auth,
) -> list[OutlookOut]:
    """Return all VitalityOutlook rows for the patient.

    If no cached rows exist for **any** horizon, compute fresh projections via
    ``compute_outlook`` (using the latest VitalitySnapshot score as
    ``current_score``) and upsert the results.  This ensures the endpoint
    always returns data on first call.

    Patient isolation: every read and write is scoped to ``patient_id`` from
    the URL path — no cross-patient data is ever returned.

    Args:
        patient_id: URL path parameter — the patient whose outlook to fetch.
        session:    Injected ``AsyncSession``.
        _auth:      API key authentication guard.

    Returns:
        A list of ``OutlookOut`` items (one per horizon: 3, 6, 12 months).
        At most three items.

    Raises:
        HTTPException: 404 when the patient does not exist.
    """
    await _require_patient(patient_id, session)

    outlook_repo = VitalityOutlookRepository(session)

    # Fetch existing rows for all horizons.
    existing_rows = []
    for horizon in _HORIZONS:
        row = await outlook_repo.latest(patient_id=patient_id, horizon_months=horizon)
        if row is not None:
            existing_rows.append(row)

    if existing_rows:
        # At least one persisted row found — return all available.
        return [OutlookOut.model_validate(r) for r in existing_rows]

    # ------------------------------------------------------------------
    # No cached outlook — compute fresh and upsert all three horizons.
    # ------------------------------------------------------------------
    vitality_repo = VitalityRepository(session)
    snapshot = await vitality_repo.get(patient_id=patient_id)

    # Use the snapshot score as current_score; fall back to 50.0 if absent.
    current_score: float = float(snapshot.score) if snapshot is not None else 50.0

    projections = compute_outlook(
        patient_id=patient_id,
        current_score=current_score,
        streak_days=0,         # conservative: no streak data yet
        protocol_adherence=0.0,
    )

    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    upserted = []
    for horizon, projected_score in projections.items():
        from app.models.vitality_outlook import VitalityOutlook

        vo = VitalityOutlook(
            patient_id=patient_id,
            horizon_months=horizon,
            projected_score=projected_score,
            narrative="",
            computed_at=now,
        )
        persisted = await outlook_repo.upsert_by_horizon(
            patient_id=patient_id, outlook=vo
        )
        upserted.append(persisted)

    return [OutlookOut.model_validate(r) for r in upserted]
