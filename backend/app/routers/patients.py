"""Patient read-only router.

Provides the six endpoints that power the mockup's Dashboard, Records,
Wearable, and Insights screens.  Every endpoint is:
  - authenticated via ``api_key_auth``
  - scoped to a single patient via ``patient_id`` path parameter
  - backed by concrete repositories (T11) — no raw SQL

Cross-patient safety: if a request targets a patient that does not exist in
the database, every endpoint returns HTTP 404 rather than an empty response.
This prevents information-leakage via the distinction between "patient exists
but has no data" vs "patient does not exist".

Vitality endpoint: loads the full patient profile from the DB, computes the
heuristic VitalityResult via ``compute_vitality``, wraps it in ``VitalityOut``,
and opportunistically upserts a ``VitalitySnapshot`` for caching.  The upsert
failure (e.g. DB write error) is silently swallowed — the computed result is
still returned to the caller (best-effort persistence).
"""

from __future__ import annotations

import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import api_key_auth
from app.db.session import get_session
from app.models.vitality_snapshot import VitalitySnapshot
from app.repositories.ehr_repo import EHRRepository
from app.repositories.patient_repo import PatientRepository
from app.repositories.vitality_repo import VitalityRepository
from app.repositories.wearable_repo import WearableRepository
from app.schemas.insights import InsightOut, InsightsListOut
from app.schemas.patient import PatientProfileOut
from app.schemas.records import EHRRecordListOut, EHRRecordOut
from app.schemas.vitality import TrendPoint, VitalityOut
from app.schemas.wearable import WearableDayOut, WearableSeriesOut
from app.services.insights import derive_insights
from app.services.vitality_engine import DISCLAIMER, compute_vitality

router = APIRouter(prefix="/patients", tags=["patients"])

# Type alias for the session dependency to keep signatures concise.
_Session = Annotated[AsyncSession, Depends(get_session)]
_Auth = Annotated[None, Depends(api_key_auth)]

# Attribute name constant used with getattr() — the repos use this pattern
# to work around mypy strict mode rejecting SQLModel attribute comparisons.
_LP_PID = "patient_id"


async def _get_lifestyle(session: AsyncSession, patient_id: str) -> Any:
    """Fetch the LifestyleProfile for a patient, or None if unavailable.

    Returns ``Any`` because ``LifestyleProfile`` is imported lazily inside the
    function body; the type is not available at the module level.  Callers
    (vitality engine, insights service) accept ``LifestyleProfile | None``
    which is satisfied at runtime.

    Isolated to a helper to keep the module-level imports clean.
    """
    try:
        from sqlalchemy import select

        from app.models.lifestyle_profile import LifestyleProfile

        pid_attr = getattr(LifestyleProfile, _LP_PID)
        stmt = select(LifestyleProfile).where(pid_attr == patient_id)
        result = await session.execute(stmt)
        return result.scalars().first()
    except Exception:  # noqa: BLE001
        return None


@router.get(
    "/{patient_id}",
    response_model=PatientProfileOut,
    tags=["patients"],
    summary="Fetch a patient's demographic profile",
)
async def get_patient_profile(
    patient_id: str,
    session: _Session,
    _auth: _Auth,
) -> PatientProfileOut:
    """Return the demographic profile for *patient_id*.

    Raises HTTP 404 if the patient does not exist — never returns empty data
    to avoid leaking information about which patient IDs are valid.

    Args:
        patient_id: Path parameter, e.g. ``PT0282``.
        session:    Injected ``AsyncSession`` (per-request).
        _auth:      ``api_key_auth`` result (validates ``X-API-Key`` header).
    """
    repo = PatientRepository(session)
    patient = await repo.get(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found.",
        )
    return PatientProfileOut.model_validate(patient)


@router.get(
    "/{patient_id}/vitality",
    response_model=VitalityOut,
    tags=["patients"],
    summary="Compute the heuristic vitality score for a patient",
)
async def get_vitality(
    patient_id: str,
    session: _Session,
    _auth: _Auth,
) -> VitalityOut:
    """Compute and return the heuristic VitalityResult for *patient_id*.

    Execution order:
    1. Fetch patient, EHR records, last 7 wearable days, lifestyle profile.
    2. Call ``compute_vitality`` (pure function — no DB access).
    3. Opportunistically upsert a ``VitalitySnapshot`` for caching.
    4. Return ``VitalityOut``.

    Raises HTTP 404 if the patient does not exist.

    Args:
        patient_id: Path parameter, e.g. ``PT0282``.
        session:    Injected ``AsyncSession``.
        _auth:      ``api_key_auth`` result.
    """
    patient_repo = PatientRepository(session)
    patient = await patient_repo.get(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found.",
        )

    ehr_repo = EHRRepository(session)
    ehr_records = await ehr_repo.list(patient_id=patient_id)

    wearable_repo = WearableRepository(session)
    wearable_days = await wearable_repo.list_recent(patient_id=patient_id, days=7)

    lifestyle = await _get_lifestyle(session, patient_id)

    result = compute_vitality(patient, ehr_records, wearable_days, lifestyle)

    # Opportunistic upsert — swallow errors so the read always succeeds.
    try:
        vitality_repo = VitalityRepository(session)
        snapshot = VitalitySnapshot(
            patient_id=patient_id,
            computed_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
            score=result.score,
            subscores=result.subscores,
            # Store risk_flags list as a JSONB dict with a "flags" key.
            risk_flags={"flags": result.risk_flags},
        )
        await vitality_repo.upsert(patient_id=patient_id, snapshot=snapshot)
        await session.commit()
    except Exception:  # noqa: BLE001
        await session.rollback()

    trend = [TrendPoint(date=tp.date, score=tp.score) for tp in result.trend]

    return VitalityOut(
        score=result.score,
        subscores=result.subscores,
        trend=trend,
        computed_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        risk_flags=result.risk_flags,
        disclaimer=DISCLAIMER,
    )


@router.get(
    "/{patient_id}/records",
    response_model=EHRRecordListOut,
    tags=["patients"],
    summary="List EHR records for a patient",
)
async def get_records(
    patient_id: str,
    session: _Session,
    _auth: _Auth,
    type: str | None = Query(default=None, alias="type"),
) -> EHRRecordListOut:
    """Return EHR records for *patient_id*, optionally filtered by type.

    Raises HTTP 404 if the patient does not exist.

    Query parameters:
        type: Optional filter — one of ``condition``, ``medication``,
              ``visit``, ``lab_panel``.

    Args:
        patient_id: Path parameter, e.g. ``PT0282``.
        session:    Injected ``AsyncSession``.
        _auth:      ``api_key_auth`` result.
        type:       Optional ``?type=lab_panel`` filter.
    """
    patient_repo = PatientRepository(session)
    patient = await patient_repo.get(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found.",
        )

    ehr_repo = EHRRepository(session)
    records = await ehr_repo.list(patient_id=patient_id, record_type=type)

    record_outs = [EHRRecordOut.model_validate(r) for r in records]
    return EHRRecordListOut(
        patient_id=patient_id,
        records=record_outs,
        total=len(record_outs),
    )


@router.get(
    "/{patient_id}/records/{record_id}",
    response_model=EHRRecordOut,
    tags=["patients"],
    summary="Fetch a single EHR record by ID",
)
async def get_single_record(
    patient_id: str,
    record_id: int,
    session: _Session,
    _auth: _Auth,
) -> EHRRecordOut:
    """Return a single EHR record by surrogate ID, scoped to *patient_id*.

    Raises HTTP 404 if either the patient does not exist or the record
    does not belong to the patient (cross-patient access returns 404, not 403,
    to avoid information leakage).

    Args:
        patient_id: Path parameter, e.g. ``PT0282``.
        record_id:  Surrogate integer PK of the EHR record.
        session:    Injected ``AsyncSession``.
        _auth:      ``api_key_auth`` result.
    """
    patient_repo = PatientRepository(session)
    patient = await patient_repo.get(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found.",
        )

    ehr_repo = EHRRepository(session)
    record = await ehr_repo.get(patient_id=patient_id, record_id=record_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EHR record {record_id} not found for patient {patient_id!r}.",
        )
    return EHRRecordOut.model_validate(record)


@router.get(
    "/{patient_id}/wearable",
    response_model=WearableSeriesOut,
    tags=["patients"],
    summary="Return recent wearable telemetry for a patient",
)
async def get_wearable(
    patient_id: str,
    session: _Session,
    _auth: _Auth,
    days: int = Query(default=7, ge=1, le=90),
) -> WearableSeriesOut:
    """Return the last *days* days of wearable telemetry for *patient_id*.

    Rows are ordered descending by date (most recent first).
    Raises HTTP 404 if the patient does not exist.

    Query parameters:
        days: Number of days to return (1–90, default 7).

    Args:
        patient_id: Path parameter, e.g. ``PT0282``.
        session:    Injected ``AsyncSession``.
        _auth:      ``api_key_auth`` result.
        days:       How many days of history to include.
    """
    patient_repo = PatientRepository(session)
    patient = await patient_repo.get(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found.",
        )

    wearable_repo = WearableRepository(session)
    wearable_days = await wearable_repo.list_recent(patient_id=patient_id, days=days)

    day_outs = [WearableDayOut.model_validate(d) for d in wearable_days]
    return WearableSeriesOut(patient_id=patient_id, days=day_outs)


@router.get(
    "/{patient_id}/insights",
    response_model=InsightsListOut,
    tags=["patients"],
    summary="Return wellness insights for a patient",
)
async def get_insights(
    patient_id: str,
    session: _Session,
    _auth: _Auth,
) -> InsightsListOut:
    """Compute and return wellness insights for *patient_id*.

    Internally calls ``compute_vitality`` then ``derive_insights``; both are
    pure functions with no DB side-effects (vitality snapshot upsert is
    intentionally omitted here — the ``/vitality`` endpoint handles that).

    Raises HTTP 404 if the patient does not exist.

    Args:
        patient_id: Path parameter, e.g. ``PT0282``.
        session:    Injected ``AsyncSession``.
        _auth:      ``api_key_auth`` result.
    """
    patient_repo = PatientRepository(session)
    patient = await patient_repo.get(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found.",
        )

    ehr_repo = EHRRepository(session)
    ehr_records = await ehr_repo.list(patient_id=patient_id)

    wearable_repo = WearableRepository(session)
    wearable_days = await wearable_repo.list_recent(patient_id=patient_id, days=7)

    lifestyle = await _get_lifestyle(session, patient_id)

    vitality_result = compute_vitality(patient, ehr_records, wearable_days, lifestyle)
    raw_insights = derive_insights(vitality_result, ehr_records, lifestyle)

    insight_outs = [
        InsightOut(
            kind=i.kind,
            severity=i.severity,
            message=i.message,
            signals=i.signals,
            prevention_signals=i.prevention_signals,
            disclaimer=i.disclaimer,
        )
        for i in raw_insights
    ]

    all_risk_flags = vitality_result.risk_flags
    all_signals: list[str] = [s for i in raw_insights for s in i.signals]
    all_prevention: list[str] = [p for i in raw_insights for p in i.prevention_signals]

    return InsightsListOut(
        patient_id=patient_id,
        insights=insight_outs,
        risk_flags=all_risk_flags,
        signals=all_signals,
        prevention_signals=all_prevention,
    )
