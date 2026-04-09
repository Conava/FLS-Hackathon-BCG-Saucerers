"""DataSource Protocol and PatientData DTO.

This module defines the pluggable data-source abstraction for Longevity+.
Any new data source (CSV, FHIR, Apple Health, Doctolib, etc.) implements the
``DataSource`` Protocol and registers itself with ``@register``. Downstream
services (``UnifiedProfileService``) never import concrete adapter classes —
they call ``get_source(name)`` instead.

Design decisions
----------------
* ``PatientData`` is a plain ``@dataclass``, not a Pydantic model. It is an
  in-process DTO that carries SQLModel instances; Pydantic validation overhead
  is unnecessary and the types are already validated at the ORM layer.
* ``DataSource`` is a ``typing.Protocol`` so any class with the right shape
  satisfies it — no inheritance required (structural subtyping).
* ``iter_patients`` is an async generator (``AsyncIterator``) rather than
  returning a list. This keeps memory bounded when iterating over 1 000+
  patients: only one ``PatientData`` bundle lives in memory at a time.
"""

from __future__ import annotations

import dataclasses
from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from app.models import DailyLog, EHRRecord, LifestyleProfile, MealLog, Patient, WearableDay


@dataclasses.dataclass
class PatientData:
    """In-process DTO bundling all data for a single patient.

    Attributes
    ----------
    patient:
        Core identity record for the patient.
    ehr_records:
        All clinical records (conditions, medications, visits, lab panels)
        loaded from the data source for this patient.
    wearable_days:
        Daily wearable telemetry aggregates, one entry per calendar day.
    lifestyle:
        Latest lifestyle survey response, or ``None`` if the source does not
        supply lifestyle data (e.g. a pure FHIR adapter).
    daily_logs:
        Quick-log records (mood, workout, sleep, water) loaded from the data
        source for this patient.  Defaults to an empty list so existing call
        sites that do not supply daily_logs remain valid.
    meal_logs:
        Meal-photo analysis records loaded from the data source for this
        patient.  Defaults to an empty list.
    """

    patient: Patient
    ehr_records: list[EHRRecord]
    wearable_days: list[WearableDay]
    lifestyle: LifestyleProfile | None
    daily_logs: list[DailyLog] = dataclasses.field(default_factory=list)
    meal_logs: list[MealLog] = dataclasses.field(default_factory=list)


@runtime_checkable
class DataSource(Protocol):
    """Protocol that every data-source adapter must satisfy.

    Structural subtyping — no ``DataSource`` import required in adapter
    modules. Declare ``name`` and implement ``iter_patients``.

    Attributes
    ----------
    name:
        Short identifier for this source (e.g. ``"csv"``, ``"fhir"``).
        Must match the key used in ``@register(name)``.

    Methods
    -------
    iter_patients:
        Async generator that yields one ``PatientData`` bundle per patient.
        Implementations must stream records rather than loading all patients
        into memory first.
    """

    name: str

    async def iter_patients(self) -> AsyncIterator[PatientData]:
        """Yield one PatientData bundle per patient, streaming."""
        ...
