"""Appointments router.

``GET /patients/{patient_id}/appointments`` — returns a stub list of upcoming
appointments for a patient, sourced via the pluggable ``AppointmentSource``
Protocol (T15).

Every route:
  - Requires ``X-API-Key`` authentication (``api_key_auth``).
  - Declares an explicit ``response_model``.
  - Is tagged ``appointments`` in OpenAPI.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.appointment_source import AppointmentSource, get_appointment_source
from app.core.security import api_key_auth
from app.db.session import get_session
from app.repositories.patient_repo import PatientRepository
from app.schemas.appointments import AppointmentCreateIn, AppointmentListOut, AppointmentOut

router = APIRouter(
    prefix="/patients/{patient_id}/appointments",
    tags=["appointments"],
)

# Type aliases for cleaner signatures.
_Session = Annotated[AsyncSession, Depends(get_session)]
_Auth = Annotated[None, Depends(api_key_auth)]


def _get_appointment_source() -> AppointmentSource:
    """Return the configured AppointmentSource (T15 StaticAppointmentSource)."""
    return get_appointment_source()


# FastAPI dependency that resolves the appointment source.
AppointmentSourceDep = Annotated[
    AppointmentSource,
    Depends(_get_appointment_source),
]


@router.get(
    "/",
    response_model=AppointmentListOut,
    tags=["appointments"],
    summary="List upcoming appointments for a patient",
)
async def list_appointments(
    patient_id: str,
    session: _Session,
    _auth: _Auth,
    source: AppointmentSourceDep,
) -> AppointmentListOut:
    """Return upcoming appointments for *patient_id*.

    The appointment list is sourced from the injected ``AppointmentSource``
    (today: static stub; future: Doctolib adapter).  Raises HTTP 404 if the
    patient does not exist to maintain consistent cross-patient isolation.

    Args:
        patient_id: Path parameter, e.g. ``PT0282``.
        session:    Injected ``AsyncSession``.
        _auth:      ``api_key_auth`` result.
        source:     Resolved ``AppointmentSource`` instance.
    """
    patient_repo = PatientRepository(session)
    patient = await patient_repo.get(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found.",
        )

    raw_appointments = await source.list_for(patient_id)
    appointments = [
        AppointmentOut(
            id=a.id,
            title=a.title,
            provider=a.provider,
            location=a.location,
            starts_at=a.starts_at,
            duration_minutes=a.duration_minutes,
            price_eur=a.price_eur,
            covered_percent=a.covered_percent,
        )
        for a in raw_appointments
    ]
    return AppointmentListOut(patient_id=patient_id, appointments=appointments)


@router.post(
    "/",
    response_model=AppointmentOut,
    status_code=status.HTTP_201_CREATED,
    tags=["appointments"],
    summary="Book a new appointment for a patient",
)
async def book_appointment(
    patient_id: str,
    body: AppointmentCreateIn,
    session: _Session,
    _auth: _Auth,
    source: AppointmentSourceDep,
) -> AppointmentOut:
    """Book a new appointment for *patient_id* via the configured ``AppointmentSource``.

    Validates that the patient exists (404 if not) to maintain consistent
    cross-patient isolation.  The booking is delegated to the injected
    ``AppointmentSource``; today this is the in-memory ``StaticAppointmentSource``
    stub; a real scheduling adapter (e.g. Doctolib) drops in with no router
    changes.

    Args:
        patient_id:       Path parameter, e.g. ``PT0100``.
        body:             Booking request body (``AppointmentCreateIn``).
        session:          Injected ``AsyncSession``.
        _auth:            ``api_key_auth`` result.
        source:           Resolved ``AppointmentSource`` instance.

    Returns:
        The booked ``AppointmentOut`` with an assigned ``id``.

    Raises:
        HTTP 404: If ``patient_id`` does not exist in the database.
    """
    patient_repo = PatientRepository(session)
    patient = await patient_repo.get(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id!r} not found.",
        )

    booked = await source.book(
        patient_id,
        title=body.title,
        provider=body.provider,
        location=body.location,
        starts_at=body.starts_at,
        duration_minutes=body.duration_minutes,
        price_eur=body.price_eur,
        covered_percent=body.covered_percent,
    )
    return AppointmentOut(
        id=booked.id,
        title=booked.title,
        provider=booked.provider,
        location=booked.location,
        starts_at=booked.starts_at,
        duration_minutes=booked.duration_minutes,
        price_eur=booked.price_eur,
        covered_percent=booked.covered_percent,
    )
