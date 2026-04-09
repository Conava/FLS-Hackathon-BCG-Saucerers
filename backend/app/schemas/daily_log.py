"""Daily log request/response DTOs.

``DailyLogIn`` is the inbound payload for logging daily wellness metrics.
All metric fields are optional — patients may log a subset of metrics at a time.

``DailyLogOut`` is the response for a single persisted log entry.
``DailyLogListOut`` wraps the paginated list returned by the history endpoint.
"""

from __future__ import annotations

import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Allowed values for workout structured fields
WorkoutType = Literal["walk", "run", "bike", "strength", "yoga", "other"]
WorkoutIntensity = Literal["low", "med", "high"]


class DailyLogIn(BaseModel):
    """Inbound payload for ``POST /v1/patients/{pid}/daily-log``.

    All metric fields are optional — patients log what they have.
    ``date`` defaults to today when omitted.
    """

    model_config = ConfigDict(from_attributes=True)

    date: datetime.date = Field(
        ...,
        description="Calendar date for this log entry (YYYY-MM-DD)",
    )
    mood_score: int | None = Field(
        None,
        ge=1,
        le=10,
        description="Self-reported mood score 1–10",
    )
    workout_minutes: int | None = Field(
        None,
        ge=0,
        description="Minutes of intentional movement or exercise",
    )
    sleep_hours: float | None = Field(
        None,
        ge=0.0,
        le=24.0,
        description="Hours of sleep the previous night",
    )
    water_glasses: int | None = Field(
        None,
        ge=0,
        description="Number of ~250 ml glasses of water consumed",
    )
    alcohol_units: int | None = Field(
        None,
        ge=0,
        description="Alcohol units consumed (1 unit ≈ 10 ml pure ethanol)",
    )

    # Structured sleep metadata (B1)
    sleep_quality: int | None = Field(
        None,
        ge=1,
        le=5,
        description="Subjective sleep quality on a 1–5 Likert scale",
    )

    # Structured workout metadata (B1)
    workout_type: WorkoutType | None = Field(
        None,
        description="Type of workout: walk/run/bike/strength/yoga/other",
    )
    workout_intensity: WorkoutIntensity | None = Field(
        None,
        description="Workout intensity: low/med/high",
    )


class DailyLogOut(BaseModel):
    """API response schema for a single persisted daily log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Daily log primary key")
    patient_id: str = Field(..., description="Patient this log belongs to")
    date: datetime.date = Field(..., description="Calendar date for this log entry")
    mood_score: int | None = Field(None, description="Self-reported mood score 1–10")
    workout_minutes: int | None = Field(None, description="Minutes of movement")
    sleep_hours: float | None = Field(None, description="Hours of sleep")
    water_glasses: int | None = Field(None, description="Glasses of water consumed")
    alcohol_units: int | None = Field(None, description="Alcohol units consumed")
    logged_at: datetime.datetime = Field(
        ...,
        description="Timestamp when this entry was created (naive UTC)",
    )

    # Structured sleep metadata (B1)
    sleep_quality: int | None = Field(
        None,
        description="Subjective sleep quality on a 1–5 Likert scale",
    )

    # Structured workout metadata (B1)
    workout_type: WorkoutType | None = Field(
        None,
        description="Type of workout: walk/run/bike/strength/yoga/other",
    )
    workout_intensity: WorkoutIntensity | None = Field(
        None,
        description="Workout intensity: low/med/high",
    )


class DailyLogListOut(BaseModel):
    """API response schema for a list of daily log entries."""

    model_config = ConfigDict(from_attributes=True)

    patient_id: str = Field(..., description="Patient the logs belong to")
    logs: list[DailyLogOut] = Field(
        default_factory=list,
        description="Daily log entries ordered by date descending",
    )
