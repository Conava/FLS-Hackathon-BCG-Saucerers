"""Survey router — POST and GET endpoints for patient surveys.

Endpoints:
  POST /patients/{patient_id}/survey
      Accepts a SurveySubmitRequest (kind + answers dict) and persists a
      SurveyResponse row.  For the "onboarding" kind, also upserts the
      relevant LifestyleProfile fields from the answers dict (defensive
      dict.get() so partial answers don't overwrite existing values with None).

  GET /patients/{patient_id}/survey?kind=...
      Returns the most recently submitted survey of the given kind (404 if
      none exist).

  GET /patients/{patient_id}/survey/history?kind=...
      Returns all surveys of the given kind, newest first.

Every endpoint:
  - requires the X-API-Key header (401 otherwise)
  - scopes all DB access to the path's patient_id
  - returns 404 for unknown patients

Cross-patient isolation is enforced at the SQL level via SurveyRepository
which extends PatientScopedRepository.
"""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import api_key_auth
from app.db.session import get_session
from app.repositories.patient_repo import PatientRepository
from app.repositories.survey_repo import SurveyRepository
from app.schemas.survey import SurveyHistoryOut, SurveyKind, SurveyResponseOut, SurveySubmitRequest

router = APIRouter(prefix="/patients", tags=["survey"])

# Annotated shortcuts — keep route signatures concise.
_Session = Annotated[AsyncSession, Depends(get_session)]
_Auth = Annotated[None, Depends(api_key_auth)]

# LifestyleProfile fields that the onboarding survey can populate.
# dict.get() is used for each so partial submissions never overwrite with None.
_ONBOARDING_LP_FIELDS = (
    "time_budget_minutes_per_day",
    "out_of_pocket_budget_eur_per_month",
    "dietary_restrictions",
    "known_allergies",
    "injuries_or_limitations",
    "smoking_status",
    "alcohol_units_weekly",
    "diet_quality_score",
    "fruit_veg_servings_daily",
    "meal_frequency_daily",
    "water_glasses_daily",
    "exercise_sessions_weekly",
    "sedentary_hrs_day",
    "stress_level",
    "sleep_satisfaction",
    "mental_wellbeing_who5",
    "self_rated_health",
)


async def _require_patient(session: AsyncSession, patient_id: str) -> None:
    """Raise HTTP 404 if patient_id does not exist in the database.

    Args:
        session:    Open ``AsyncSession``.
        patient_id: The patient_id to validate.

    Raises:
        HTTPException: 404 when the patient is not found.
    """
    repo = PatientRepository(session)
    patient = await repo.get(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found.",
        )


async def _upsert_lifestyle_from_onboarding(
    session: AsyncSession,
    patient_id: str,
    answers: dict,
) -> None:
    """Apply onboarding survey answers to the patient's LifestyleProfile.

    Creates the LifestyleProfile row if it does not yet exist.  Only fields
    present in *answers* are written; missing keys leave existing values
    unchanged (defensive dict.get() pattern).

    Args:
        session:    Open ``AsyncSession``.
        patient_id: The patient whose LifestyleProfile is updated.
        answers:    The raw answers dict from the onboarding submission.
    """
    from sqlalchemy import select

    from app.models.lifestyle_profile import LifestyleProfile

    # Fetch or create the LifestyleProfile.
    pid_attr = getattr(LifestyleProfile, "patient_id")
    stmt = select(LifestyleProfile).where(pid_attr == patient_id)
    result = await session.execute(stmt)
    lp = result.scalars().first()

    if lp is None:
        lp = LifestyleProfile(
            patient_id=patient_id,
            survey_date=datetime.datetime.now(datetime.UTC).replace(tzinfo=None).date(),
        )
        session.add(lp)
        await session.flush()

    # Apply whichever fields are present in answers — never write None.
    for field in _ONBOARDING_LP_FIELDS:
        value = answers.get(field)
        if value is not None:
            object.__setattr__(lp, field, value)

    await session.flush()


@router.post(
    "/{patient_id}/survey",
    response_model=SurveyResponseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a survey response",
    tags=["survey"],
)
async def post_survey(
    patient_id: str,
    body: SurveySubmitRequest,
    session: _Session,
    _auth: _Auth,
) -> SurveyResponseOut:
    """Persist a new survey response for *patient_id*.

    When ``kind`` is "onboarding" the relevant ``LifestyleProfile`` fields
    are also updated in the same DB transaction.

    Args:
        patient_id: Path parameter — the patient submitting the survey.
        body:       Request body containing ``kind`` and ``answers``.
        session:    Injected ``AsyncSession``.
        _auth:      ``api_key_auth`` result (validates ``X-API-Key`` header).

    Returns:
        The persisted ``SurveyResponseOut`` with id, kind, submitted_at, answers.

    Raises:
        HTTPException: 404 if the patient does not exist.
    """
    await _require_patient(session, patient_id)

    from app.models.survey_response import SurveyResponse

    survey_row = SurveyResponse(
        patient_id=patient_id,
        kind=str(body.kind),
        answers=body.answers,
        submitted_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
    )

    repo = SurveyRepository(session)
    created = await repo.create(patient_id=patient_id, survey=survey_row)

    # For onboarding surveys, backfill the LifestyleProfile.
    if body.kind == SurveyKind.onboarding:
        await _upsert_lifestyle_from_onboarding(session, patient_id, body.answers)

    await session.commit()

    return SurveyResponseOut.model_validate(created)


@router.get(
    "/{patient_id}/survey/history",
    response_model=SurveyHistoryOut,
    summary="Return all surveys of a given kind for a patient",
    tags=["survey"],
)
async def get_survey_history(
    patient_id: str,
    session: _Session,
    _auth: _Auth,
    kind: SurveyKind = Query(..., description="Survey kind: onboarding | weekly | quarterly"),
) -> SurveyHistoryOut:
    """Return all surveys of *kind* submitted by *patient_id*, newest first.

    Returns an empty ``responses`` list (not 404) when the patient exists but
    has no surveys of the requested kind — this mirrors the empty-list
    convention used by list endpoints throughout the API.

    Args:
        patient_id: Path parameter.
        session:    Injected ``AsyncSession``.
        _auth:      ``api_key_auth`` result.
        kind:       ``?kind=weekly`` query parameter.

    Returns:
        ``SurveyHistoryOut`` with ``patient_id`` and ``responses`` list.

    Raises:
        HTTPException: 404 if the patient does not exist.
    """
    await _require_patient(session, patient_id)

    repo = SurveyRepository(session)
    rows = await repo.history(patient_id=patient_id, kind=str(kind))

    response_outs = [SurveyResponseOut.model_validate(r) for r in rows]
    return SurveyHistoryOut(patient_id=patient_id, responses=response_outs)


@router.get(
    "/{patient_id}/survey",
    response_model=SurveyResponseOut,
    summary="Return the latest survey of a given kind for a patient",
    tags=["survey"],
)
async def get_latest_survey(
    patient_id: str,
    session: _Session,
    _auth: _Auth,
    kind: SurveyKind = Query(..., description="Survey kind: onboarding | weekly | quarterly"),
) -> SurveyResponseOut:
    """Return the most recently submitted survey of *kind* for *patient_id*.

    Args:
        patient_id: Path parameter.
        session:    Injected ``AsyncSession``.
        _auth:      ``api_key_auth`` result.
        kind:       ``?kind=weekly`` query parameter.

    Returns:
        The most recent ``SurveyResponseOut``.

    Raises:
        HTTPException: 404 if the patient does not exist or has no surveys
            of the requested kind.
    """
    await _require_patient(session, patient_id)

    repo = SurveyRepository(session)
    row = await repo.latest_by_kind(patient_id=patient_id, kind=str(kind))

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {kind!r} survey found for patient {patient_id!r}.",
        )

    return SurveyResponseOut.model_validate(row)
