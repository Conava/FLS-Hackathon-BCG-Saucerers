"""Protocol router — generate, get, and complete-action endpoints.

Endpoints:
  POST /v1/patients/{patient_id}/protocol/generate
    Generates a new weekly wellness protocol via ProtocolGeneratorService
    (structured LLM call). Returns ProtocolOut.

  GET  /v1/patients/{patient_id}/protocol
    Returns the patient's active Protocol (status="active"). 404 if none.

  POST /v1/patients/{patient_id}/protocol/complete-action
    Marks a ProtocolAction as completed (increments streak_days, sets
    completed_today=True), then recomputes VitalityOutlook in-process and
    persists the three horizon projections (3, 6, 12 months).

All endpoints:
  - Require X-API-Key authentication (``api_key_auth``).
  - Scope reads and writes to ``patient_id`` at the SQL level (via repos).
  - Are tagged ``protocol`` in OpenAPI.

PHI policy: no patient name or free-text fields are logged.
Stack: FastAPI + SQLModel + SQLAlchemy 2.0 async + Pydantic v2.
"""

from __future__ import annotations

import datetime
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import FakeLLMProvider, LLMProvider
from app.core.logging import get_logger
from app.core.security import api_key_auth
from app.db.session import get_session
from app.models.vitality_outlook import VitalityOutlook
from app.repositories.outlook_repo import VitalityOutlookRepository
from app.repositories.protocol_repo import ProtocolActionRepository, ProtocolRepository
from app.schemas.protocol import (
    CompleteActionRequest,
    CompleteActionResponse,
    ProtocolActionOut,
    ProtocolOut,
)
from app.services.outlook_engine import compute_outlook
from app.services.protocol_generator import ProtocolGeneratorService

_logger: logging.Logger = get_logger(__name__)

router = APIRouter(
    prefix="/patients/{patient_id}/protocol",
    tags=["protocol"],
)

# Type aliases for cleaner signatures.
_Session = Annotated[AsyncSession, Depends(get_session)]
_Auth = Annotated[None, Depends(api_key_auth)]


def get_llm() -> LLMProvider:
    """Return a FakeLLMProvider by default.

    This dependency is overridden in tests and in main.py (where it returns
    the settings-configured provider).  The default here enables the router
    to work in isolation (e.g., when mounted on a mini-app in tests).
    """
    return FakeLLMProvider()


_LLM = Annotated[LLMProvider, Depends(get_llm)]


# ---------------------------------------------------------------------------
# POST /generate
# ---------------------------------------------------------------------------


@router.post(
    "/generate",
    response_model=ProtocolOut,
    summary="Generate a weekly wellness protocol for a patient",
)
async def generate_protocol(
    patient_id: str,
    session: _Session,
    _auth: _Auth,
    llm: _LLM,
) -> ProtocolOut:
    """Generate and persist a new weekly protocol for *patient_id*.

    Calls ``ProtocolGeneratorService`` which assembles a context from the
    patient's ``LifestyleProfile``, latest ``VitalitySnapshot``, and last-7-day
    ``DailyLog`` entries, then asks the LLM for a structured ``GeneratedProtocol``.

    Args:
        patient_id: Path parameter.
        session:    Injected ``AsyncSession``.
        _auth:      ``api_key_auth`` result.
        llm:        Injected ``LLMProvider`` (Fake in tests, Gemini in prod).

    Returns:
        ``ProtocolOut`` with the persisted protocol and its actions.

    Raises:
        HTTPException 422: If ``LifestyleProfile`` is missing or LLM constraints
            are violated (e.g. too many actions, time budget exceeded).
    """
    protocol_repo = ProtocolRepository(session)
    action_repo = ProtocolActionRepository(session)

    svc = ProtocolGeneratorService(
        llm_provider=llm,
        protocol_repo=protocol_repo,
        action_repo=action_repo,
        session=session,
    )

    try:
        protocol = await svc.generate_for_patient(patient_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    _logger.info(
        "protocol_generated_via_router",
        extra={"protocol_id": protocol.id},
    )

    # Load actions for the response
    actions = await action_repo.list_for_patient(patient_id=patient_id)
    # Filter to only actions belonging to this protocol
    protocol_actions = [a for a in actions if a.protocol_id == protocol.id]

    action_outs = [
        ProtocolActionOut(
            id=a.id,  # type: ignore[arg-type]
            protocol_id=a.protocol_id,
            category=a.category,
            title=a.title,
            target=a.target_value,
            rationale=a.rationale,
            completed_today=a.completed_today,
            streak_days=a.streak_days,
        )
        for a in protocol_actions
    ]

    return ProtocolOut(
        id=protocol.id,  # type: ignore[arg-type]
        patient_id=protocol.patient_id,
        created_at=protocol.created_at,
        actions=action_outs,
    )


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=ProtocolOut,
    summary="Get the active protocol for a patient",
)
async def get_protocol(
    patient_id: str,
    session: _Session,
    _auth: _Auth,
) -> ProtocolOut:
    """Return the patient's current active protocol.

    Fetches the most recently created Protocol with ``status="active"`` for
    the given patient.

    Args:
        patient_id: Path parameter.
        session:    Injected ``AsyncSession``.
        _auth:      ``api_key_auth`` result.

    Returns:
        ``ProtocolOut`` with the active protocol and its actions.

    Raises:
        HTTPException 404: If no active protocol exists for this patient.
    """
    protocol_repo = ProtocolRepository(session)
    action_repo = ProtocolActionRepository(session)

    protocol = await protocol_repo.get_active(patient_id=patient_id)
    if protocol is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active protocol found for patient {patient_id!r}.",
        )

    # Load actions belonging to this specific protocol
    all_actions = await action_repo.list_for_patient(patient_id=patient_id)
    protocol_actions = [a for a in all_actions if a.protocol_id == protocol.id]

    action_outs = [
        ProtocolActionOut(
            id=a.id,  # type: ignore[arg-type]
            protocol_id=a.protocol_id,
            category=a.category,
            title=a.title,
            target=a.target_value,
            rationale=a.rationale,
            completed_today=a.completed_today,
            streak_days=a.streak_days,
        )
        for a in protocol_actions
    ]

    return ProtocolOut(
        id=protocol.id,  # type: ignore[arg-type]
        patient_id=protocol.patient_id,
        created_at=protocol.created_at,
        actions=action_outs,
    )


# ---------------------------------------------------------------------------
# POST /complete-action
# ---------------------------------------------------------------------------


@router.post(
    "/complete-action",
    response_model=CompleteActionResponse,
    summary="Mark a protocol action as completed and recompute outlook",
)
async def complete_action(
    patient_id: str,
    body: CompleteActionRequest,
    session: _Session,
    _auth: _Auth,
) -> CompleteActionResponse:
    """Mark a ProtocolAction as completed and trigger a VitalityOutlook recompute.

    Steps:
    1. Confirm the action belongs to the patient (two-step isolation via
       ``ProtocolActionRepository.get_for_patient``).
    2. Increment ``streak_days`` and set ``completed_today=True`` via
       ``ProtocolActionRepository.update_streak``.
    3. Compute a fresh ``VitalityOutlook`` projection using
       ``compute_outlook`` (pure math — no LLM call).
    4. Persist the three horizon projections (3, 6, 12 months) via
       ``VitalityOutlookRepository.upsert_by_horizon``.
    5. Return ``CompleteActionResponse``.

    Args:
        patient_id: Path parameter.
        body:       ``CompleteActionRequest`` with the ``action_id`` to complete.
        session:    Injected ``AsyncSession``.
        _auth:      ``api_key_auth`` result.

    Returns:
        ``CompleteActionResponse`` with the updated streak and completion timestamp.

    Raises:
        HTTPException 404: If the action does not exist or belongs to a
            different patient (cross-patient isolation).
    """
    action_repo = ProtocolActionRepository(session)
    outlook_repo = VitalityOutlookRepository(session)

    # Step 1: Confirm the action belongs to the patient (two-step isolation)
    existing_action = await action_repo.get_for_patient(
        patient_id=patient_id,
        action_id=body.action_id,
    )
    if existing_action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"ProtocolAction {body.action_id!r} not found for patient "
                f"{patient_id!r}."
            ),
        )

    # Step 2: Increment streak and mark completed
    new_streak = existing_action.streak_days + 1
    updated_action = await action_repo.update_streak(
        patient_id=patient_id,
        action_id=body.action_id,
        streak_days=new_streak,
        completed_today=True,
    )
    if updated_action is None:
        # Should not happen — we just confirmed it exists
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ProtocolAction {body.action_id!r} could not be updated.",
        )

    completed_at = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

    _logger.info(
        "protocol_action_completed",
        extra={
            "action_id": body.action_id,
            "new_streak_days": new_streak,
        },
    )

    # Step 3: Compute a fresh VitalityOutlook projection
    # Use a default score of 70.0 when no snapshot exists — this is a
    # best-effort recompute; a full score would require loading VitalitySnapshot.
    current_score = await _get_current_vitality_score(session, patient_id)

    # Protocol adherence is estimated from the fraction of actions completed
    # today vs total actions in the patient's protocol.
    all_actions = await action_repo.list_for_patient(patient_id=patient_id)
    total_actions = max(1, len(all_actions))
    completed_count = sum(1 for a in all_actions if a.completed_today)
    # Include the just-updated action in the count
    if not updated_action.completed_today:
        completed_count += 1
    protocol_adherence = completed_count / total_actions

    projections = compute_outlook(
        patient_id=patient_id,
        current_score=current_score,
        streak_days=new_streak,
        protocol_adherence=protocol_adherence,
    )

    # Step 4: Persist the three horizon projections
    for horizon_months, projected_score in projections.items():
        outlook = VitalityOutlook(
            patient_id=patient_id,
            horizon_months=horizon_months,
            projected_score=projected_score,
            narrative="",  # narrator LLM call is done in T21
            computed_at=completed_at,
        )
        await outlook_repo.upsert_by_horizon(
            patient_id=patient_id,
            outlook=outlook,
        )

    return CompleteActionResponse(
        action_id=body.action_id,
        streak_days=new_streak,
        completed_at=completed_at,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_current_vitality_score(
    session: AsyncSession,
    patient_id: str,
) -> float:
    """Load the patient's current vitality score from VitalitySnapshot (if any).

    Falls back to 70.0 (a reasonable default) when no snapshot row exists.
    The score is used as the baseline for the outlook recompute triggered by
    a protocol action completion event.

    Args:
        session:    AsyncSession for DB access.
        patient_id: The patient whose score to load.

    Returns:
        The latest ``VitalitySnapshot.score`` or ``70.0`` if no snapshot found.
    """
    from sqlalchemy import select

    from app.models.vitality_snapshot import VitalitySnapshot

    pid_attr = getattr(VitalitySnapshot, "patient_id")
    stmt = select(VitalitySnapshot).where(pid_attr == patient_id)
    result = await session.execute(stmt)
    snapshot = result.scalars().first()

    if snapshot is not None:
        return float(snapshot.score)
    return 70.0
