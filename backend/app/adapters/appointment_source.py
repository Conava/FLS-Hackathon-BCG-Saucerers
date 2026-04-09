"""AppointmentSource Protocol and static fixture stub.

This module provides a pluggable Protocol for appointment data sources and a
``StaticAppointmentSource`` implementation that returns deterministic fixture
data keyed by ``patient_id``.  Tomorrow a ``DoctolibAppointmentSource`` drops
in with zero downstream changes.

Design decisions
----------------
* ``Appointment`` is a plain ``@dataclass`` (no Pydantic), mirroring the
  ``PatientData`` pattern in ``base.py``.  It is an in-process DTO; validation
  overhead is unnecessary.
* ``AppointmentSource`` is a ``@runtime_checkable`` Protocol for structural
  subtyping — implementations do not need to import or inherit from this class.
* ``starts_at`` is always a naive ``datetime`` (UTC assumed).  Timezone
  awareness is deferred to a real scheduling backend.
* Wellness framing: appointment titles and provider names use clinical-service
  language ("Panel", "Assessment") rather than diagnostic verbs to stay within
  MDR Class IIa boundaries.

Fixture content (from mockup index.html, confirmed against spec):
  PT0282 (Anna Weber):
    1. Cardio-Prevention Panel — Dr. Mehlhorn, Hamburg-Eppendorf, 14 Apr 14:30, 45 min, €79, 80%
    2. Sleep Assessment       — Dr. Klein, Tele-consult, 17 Apr 09:00, 30 min, €45, 80%
  Other patients:
    1. Annual Check-up        — no billing info, 22 Jun 10:00
"""

from __future__ import annotations

import dataclasses
import datetime as dt
from typing import Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Appointment DTO
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Appointment:
    """Flat DTO for a single appointment slot.

    Attributes
    ----------
    id:
        Stable opaque identifier for this appointment (e.g. ``"appt-pt0282-cardio"``).
    title:
        Human-readable appointment name using wellness framing.
    provider:
        Attending clinician or service provider name.
    location:
        Physical location or modality (e.g. ``"Hamburg-Eppendorf"``,
        ``"Tele-consult"``).
    starts_at:
        Naive UTC datetime for the appointment start.  No tzinfo attached.
    duration_minutes:
        Expected duration in minutes.
    price_eur:
        Out-of-pocket price in EUR, or ``None`` if not applicable.
    covered_percent:
        Insurance coverage percentage (0–100), or ``None`` if not applicable.
    """

    id: str
    title: str
    provider: str
    location: str
    starts_at: dt.datetime  # naive UTC
    duration_minutes: int
    price_eur: float | None
    covered_percent: int | None


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class AppointmentSource(Protocol):
    """Protocol for pluggable appointment data sources.

    Any class with a ``name`` attribute and a ``list_for`` coroutine satisfies
    this Protocol — no inheritance required (structural subtyping).

    Attributes
    ----------
    name:
        Short identifier for this source (e.g. ``"static"``, ``"doctolib"``).

    Methods
    -------
    list_for:
        Return the upcoming appointments for a specific patient.  Callers must
        not assume any particular ordering; the static stub orders by
        ``starts_at`` ascending.
    """

    name: str

    async def list_for(self, patient_id: str) -> list[Appointment]:
        """Return upcoming appointments for ``patient_id``."""
        ...


# ---------------------------------------------------------------------------
# Static fixture implementation
# ---------------------------------------------------------------------------

# Pre-built fixture slots for PT0282 (Anna Weber), matching the mockup.
_PT0282_APPOINTMENTS: list[Appointment] = [
    Appointment(
        id="appt-pt0282-cardio",
        title="Cardio-Prevention Panel",
        provider="Dr. Mehlhorn",
        location="Hamburg-Eppendorf",
        starts_at=dt.datetime(2026, 4, 14, 14, 30),  # naive UTC
        duration_minutes=45,
        price_eur=79.0,
        covered_percent=80,
    ),
    Appointment(
        id="appt-pt0282-sleep",
        title="Sleep Assessment",
        provider="Dr. Klein",
        location="Tele-consult",
        starts_at=dt.datetime(2026, 4, 17, 9, 0),  # naive UTC
        duration_minutes=30,
        price_eur=45.0,
        covered_percent=80,
    ),
]

# Generic fallback slot for all other patients.
_GENERIC_APPOINTMENT = Appointment(
    id="appt-generic-checkup",
    title="Annual Check-up",
    provider="Dr. Kessler",
    location="Clinic Eppendorf",
    starts_at=dt.datetime(2026, 6, 22, 10, 0),  # naive UTC
    duration_minutes=60,
    price_eur=None,
    covered_percent=None,
)


class StaticAppointmentSource:
    """Deterministic fixture-backed implementation of ``AppointmentSource``.

    Returns pre-defined appointments keyed by ``patient_id``:

    * ``"PT0282"`` → Cardio-Prevention Panel + Sleep Assessment (matches mockup).
    * Any other ID → one generic Annual Check-up.

    No external I/O; safe to call in unit tests and during local development
    before a real scheduling integration is wired in.
    """

    name = "static"

    async def list_for(self, patient_id: str) -> list[Appointment]:
        """Return upcoming appointments for ``patient_id``.

        Parameters
        ----------
        patient_id:
            Patient identifier (e.g. ``"PT0282"``).  Matching is exact.

        Returns
        -------
        list[Appointment]
            Ordered by ``starts_at`` ascending.  Always returns at least one
            appointment.
        """
        if patient_id == "PT0282":
            # Return new list to prevent mutation of the module-level constant.
            return list(_PT0282_APPOINTMENTS)
        return [_GENERIC_APPOINTMENT]


# ---------------------------------------------------------------------------
# Module-level default singleton + public accessor
# ---------------------------------------------------------------------------

_default: AppointmentSource = StaticAppointmentSource()


def get_appointment_source() -> AppointmentSource:
    """Return the default ``AppointmentSource`` singleton.

    Returns
    -------
    AppointmentSource
        The module-level default instance (currently ``StaticAppointmentSource``).
        Swap the ``_default`` binding or override this function during tests to
        inject an alternative implementation.
    """
    return _default


__all__ = [
    "Appointment",
    "AppointmentSource",
    "StaticAppointmentSource",
    "get_appointment_source",
]
