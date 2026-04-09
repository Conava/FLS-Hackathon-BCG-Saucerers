"""Appointment response DTOs.

Appointments are sourced from the pluggable ``AppointmentSource`` Protocol
(T15). Today backed by a static stub; future adapters (Doctolib, etc.) return
the same shape.

``price_eur`` and ``covered_percent`` are optional — some appointments may be
fully covered (zero out-of-pocket) or pricing may be unavailable in the stub.
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field


class AppointmentOut(BaseModel):
    """Response schema for a single appointment."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Appointment identifier (stub: string slug)")
    title: str = Field(..., description="Appointment title / service name")
    provider: str = Field(..., description="Healthcare provider name")
    location: str = Field(..., description="Clinic or virtual location")
    starts_at: datetime.datetime = Field(..., description="Appointment start time (UTC)")
    duration_minutes: int = Field(..., description="Duration in minutes")
    price_eur: float | None = Field(None, description="Out-of-pocket price in EUR")
    covered_percent: int | None = Field(
        None,
        description="Insurance coverage percentage (0–100)",
    )


class AppointmentListOut(BaseModel):
    """List of upcoming appointments for a patient."""

    model_config = ConfigDict(from_attributes=True)

    patient_id: str = Field(..., description="Patient identifier")
    appointments: list[AppointmentOut] = Field(
        default_factory=list,
        description="Upcoming appointments ordered by start time ascending",
    )
