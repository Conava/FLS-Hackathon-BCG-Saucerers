"""Daily log router — quick wellness logging for patients.

Provides two endpoints:
  - ``POST /patients/{patient_id}/daily-log`` — create a new daily log entry
  - ``GET  /patients/{patient_id}/daily-log?from=YYYY-MM-DD&to=YYYY-MM-DD``
    — list entries within an inclusive date window

Cross-patient safety: every read and write operation flows through
``DailyLogRepository``, which enforces ``WHERE patient_id = :pid`` at the
SQL level.  The FK constraint on ``DailyLog.patient_id`` additionally
rejects writes for non-existent patients.

Field mapping note: the ``DailyLog`` SQLModel uses ``mood`` and ``water_ml``
(int millilitres), while the public API DTOs use ``mood_score`` and
``water_glasses`` (int, ~250 ml glasses).  The router translates on every
read and write:
  - mood_score → mood (stored directly; no scale conversion)
  - mood → mood_score (returned as-is)
  - water_glasses → water_ml (multiply by 250)
  - water_ml → water_glasses (divide by 250, round)

The ``date`` field on the DTO is derived from ``logged_at.date()`` on reads,
and ``logged_at`` is set to midnight-UTC of the requested date on writes.
"""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import api_key_auth
from app.db.session import get_session
from app.models.daily_log import DailyLog
from app.repositories.daily_log_repo import DailyLogRepository
from app.schemas.daily_log import DailyLogIn, DailyLogListOut, DailyLogOut

router = APIRouter(prefix="/patients", tags=["daily-log"])

# Type aliases for the two common injected dependencies.
_Session = Annotated[AsyncSession, Depends(get_session)]
_Auth = Annotated[None, Depends(api_key_auth)]


# ---------------------------------------------------------------------------
# Field-mapping helpers
# ---------------------------------------------------------------------------


def _daily_log_in_to_model(patient_id: str, payload: DailyLogIn) -> DailyLog:
    """Convert an inbound ``DailyLogIn`` DTO to a ``DailyLog`` model instance.

    ``mood_score`` is stored directly in ``mood`` (no scale conversion).
    ``water_glasses`` is stored as ``water_ml`` by multiplying by 250.
    ``logged_at`` is set to midnight UTC for the requested date.

    Args:
        patient_id: The patient this log belongs to.
        payload:    The validated inbound DTO.

    Returns:
        A ``DailyLog`` instance ready to be passed to the repository.
    """
    # Derive logged_at from the requested date (midnight naive UTC).
    logged_at = datetime.datetime(
        payload.date.year,
        payload.date.month,
        payload.date.day,
        0, 0, 0,
    )

    # mood_score 1-10 is stored directly in mood (None stays None).
    # The model column accepts any int — the 1-5 comment in the model is a
    # documentation hint for the original design but no DB constraint is
    # enforced.  Storing the full 1-10 scale avoids a lossy conversion that
    # would break the lossless API contract.
    mood: int | None = payload.mood_score

    # water_glasses → water_ml (None stays None)
    water_ml: int | None = None
    if payload.water_glasses is not None:
        water_ml = payload.water_glasses * 250

    # alcohol_units: schema is int, model is float — cast safely
    alcohol_units: float | None = None
    if payload.alcohol_units is not None:
        alcohol_units = float(payload.alcohol_units)

    return DailyLog(
        patient_id=patient_id,
        logged_at=logged_at,
        mood=mood,
        workout_minutes=payload.workout_minutes,
        sleep_hours=payload.sleep_hours,
        water_ml=water_ml,
        alcohol_units=alcohol_units,
        sleep_quality=payload.sleep_quality,
        workout_type=payload.workout_type,
        workout_intensity=payload.workout_intensity,
    )


def _model_to_daily_log_out(log: DailyLog) -> DailyLogOut:
    """Convert a persisted ``DailyLog`` model to the public ``DailyLogOut`` DTO.

    ``mood`` is returned as-is as ``mood_score`` (no scale conversion).
    ``water_ml`` is converted to ``water_glasses`` by dividing by 250.
    ``date`` is derived from ``logged_at.date()``.

    Args:
        log: The persisted ``DailyLog`` instance (id is populated).

    Returns:
        A ``DailyLogOut`` DTO suitable for the HTTP response.
    """
    # mood is stored as the original mood_score value (1-10 scale).
    mood_score: int | None = log.mood

    # water_ml → water_glasses (None stays None)
    water_glasses: int | None = None
    if log.water_ml is not None:
        water_glasses = round(log.water_ml / 250)

    # alcohol_units: model is float, schema is int — round to nearest int
    alcohol_units: int | None = None
    if log.alcohol_units is not None:
        alcohol_units = round(log.alcohol_units)

    return DailyLogOut(
        id=log.id,
        patient_id=log.patient_id,
        date=log.logged_at.date(),
        mood_score=mood_score,
        workout_minutes=log.workout_minutes,
        sleep_hours=log.sleep_hours,
        water_glasses=water_glasses,
        alcohol_units=alcohol_units,
        logged_at=log.logged_at,
        sleep_quality=log.sleep_quality,
        workout_type=log.workout_type,
        workout_intensity=log.workout_intensity,
    )


# ---------------------------------------------------------------------------
# POST — create a new daily log entry
# ---------------------------------------------------------------------------


@router.post(
    "/{patient_id}/daily-log",
    response_model=DailyLogOut,
    status_code=201,
    summary="Create a new daily log entry for a patient",
    tags=["daily-log"],
)
async def create_daily_log(
    patient_id: str,
    payload: DailyLogIn,
    session: _Session,
    _auth: _Auth,
) -> DailyLogOut:
    """Persist a new quick-log entry and return the created record.

    Accepts a partial or full set of wellness metrics for a given date.
    Fields omitted from the request body are stored as ``NULL`` — callers
    may log a subset of metrics at a time.

    The FK constraint on ``DailyLog.patient_id`` will raise an
    ``IntegrityError`` (propagated as HTTP 422 by FastAPI's exception handler)
    if the patient does not exist.  This is intentional: the endpoint is only
    called after the client has verified the patient exists via the profile
    endpoint.

    Args:
        patient_id: Path parameter identifying the patient.
        payload:    Validated request body (``DailyLogIn``).
        session:    Injected ``AsyncSession``.
        _auth:      ``api_key_auth`` result (validates ``X-API-Key`` header).

    Returns:
        The persisted ``DailyLogOut`` DTO with ``id`` and ``logged_at`` populated.
    """
    log = _daily_log_in_to_model(patient_id, payload)
    repo = DailyLogRepository(session)
    persisted = await repo.create(patient_id=patient_id, log=log)
    await session.commit()
    return _model_to_daily_log_out(persisted)


# ---------------------------------------------------------------------------
# GET — list log entries within a date window
# ---------------------------------------------------------------------------


@router.get(
    "/{patient_id}/daily-log",
    response_model=DailyLogListOut,
    summary="List daily log entries for a patient within a date range",
    tags=["daily-log"],
)
async def list_daily_logs(
    patient_id: str,
    session: _Session,
    _auth: _Auth,
    from_date: Annotated[
        datetime.date,
        Query(alias="from", description="Start of date range (inclusive, YYYY-MM-DD)"),
    ],
    to_date: Annotated[
        datetime.date,
        Query(alias="to", description="End of date range (inclusive, YYYY-MM-DD)"),
    ],
) -> DailyLogListOut:
    """Return daily log entries for *patient_id* within an inclusive date window.

    Both ``from`` and ``to`` are inclusive.  Only entries whose ``logged_at``
    date falls within ``[from, to]`` are returned.  Entries are ordered by
    ``logged_at ASC`` (oldest first).

    Query parameters:
        from: Start date (YYYY-MM-DD, inclusive).
        to:   End date (YYYY-MM-DD, inclusive).

    Args:
        patient_id: Path parameter identifying the patient.
        session:    Injected ``AsyncSession``.
        _auth:      ``api_key_auth`` result.
        from_date:  Start of the date window.
        to_date:    End of the date window.

    Returns:
        ``DailyLogListOut`` containing the patient_id and list of log entries.
    """
    # Convert dates to naive UTC datetimes — start of day for from, end of day for to.
    from_dt = datetime.datetime(from_date.year, from_date.month, from_date.day, 0, 0, 0)
    to_dt = datetime.datetime(to_date.year, to_date.month, to_date.day, 23, 59, 59)

    repo = DailyLogRepository(session)
    logs = await repo.list_by_date_range(
        patient_id=patient_id,
        from_dt=from_dt,
        to_dt=to_dt,
    )

    log_outs = [_model_to_daily_log_out(log) for log in logs]
    return DailyLogListOut(patient_id=patient_id, logs=log_outs)
