"""Appointments router.

``GET /patients/{patient_id}/appointments`` — returns a stub list of upcoming
appointments for a patient, sourced via the pluggable ``AppointmentSource``
Protocol (T15).

If T15 has not been implemented yet, a local fallback stub is used so this
router can be included in tests independently of T15's merge status.

Every route:
  - Requires ``X-API-Key`` authentication (``api_key_auth``).
  - Declares an explicit ``response_model``.
  - Is tagged ``appointments`` in OpenAPI.
"""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import api_key_auth
from app.db.session import get_session
from app.repositories.patient_repo import PatientRepository
from app.schemas.appointments import AppointmentListOut, AppointmentOut

router = APIRouter(
    prefix="/patients/{patient_id}/appointments",
    tags=["appointments"],
)

# Type aliases for cleaner signatures.
_Session = Annotated[AsyncSession, Depends(get_session)]
_Auth = Annotated[None, Depends(api_key_auth)]


# ---------------------------------------------------------------------------
# AppointmentSource dependency — uses T15 when available, falls back to stub
# ---------------------------------------------------------------------------


class _FallbackAppointmentSource:
    """Minimal static stub used when T15 (appointment_source.py) is absent.

    PT0282 (Anna) gets 2 upcoming appointments; all other patients get 1.
    Dates are fixed relative to 2026-04-10 so tests are deterministic.
    """

    async def list_for(self, patient_id: str) -> list[AppointmentOut]:
        base = datetime.datetime(2026, 4, 15, 9, 0, 0)
        shared = AppointmentOut(
            id=f"apt-{patient_id}-001",
            title="Annual Wellness Check",
            provider="Dr. Müller",
            location="Hamburg Medical Centre",
            starts_at=base,
            duration_minutes=30,
            price_eur=0.0,
            covered_percent=100,
        )
        if patient_id == "PT0282":
            lipid = AppointmentOut(
                id="apt-PT0282-002",
                title="Lipid Prevention Panel",
                provider="Dr. Schmidt",
                location="Hamburg Cardiology Clinic",
                starts_at=datetime.datetime(2026, 4, 22, 14, 0, 0),
                duration_minutes=45,
                price_eur=20.0,
                covered_percent=80,
            )
            return [shared, lipid]
        return [shared]


def _get_appointment_source() -> _FallbackAppointmentSource:
    """Return the configured AppointmentSource.

    Tries to import ``get_appointment_source`` from ``app.adapters.appointment_source``
    (T15).  Falls back to the local stub when T15 is not yet available.

    The ``cast`` ensures mypy treats the returned object as
    ``_FallbackAppointmentSource`` regardless of the imported type; both share
    the ``list_for(patient_id)`` interface at runtime.
    """
    from typing import cast

    try:
        from app.adapters.appointment_source import get_appointment_source

        return cast(_FallbackAppointmentSource, get_appointment_source())
    except ImportError:
        return _FallbackAppointmentSource()


# FastAPI dependency that resolves the appointment source.
AppointmentSourceDep = Annotated[
    _FallbackAppointmentSource,
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

    appointments = await source.list_for(patient_id)
    return AppointmentListOut(patient_id=patient_id, appointments=appointments)
