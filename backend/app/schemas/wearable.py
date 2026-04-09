"""Wearable telemetry response DTOs.

Columns mirror the ``wearable_telemetry_1.csv`` headers:
  patient_id, date, resting_hr_bpm, hrv_rmssd_ms, steps, active_minutes,
  sleep_duration_hrs, sleep_quality_score, deep_sleep_pct, spo2_avg_pct,
  calories_burned_kcal

All numeric fields are ``float | None`` to be robust to missing sensor data.
``steps``, ``active_minutes``, ``sleep_quality_score`` are stored as ints in
the model but accepted as floats here for flexibility (coerced on validation).
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field


class WearableDayOut(BaseModel):
    """Response schema for a single day of wearable telemetry data."""

    model_config = ConfigDict(from_attributes=True)

    patient_id: str = Field(..., description="Patient identifier")
    date: datetime.date = Field(..., description="Calendar date for this measurement")

    # Heart metrics
    resting_hr_bpm: float | None = Field(None, description="Resting heart rate (bpm)")
    hrv_rmssd_ms: float | None = Field(None, description="HRV RMSSD in milliseconds")

    # Activity metrics
    steps: int | None = Field(None, description="Daily step count")
    active_minutes: int | None = Field(None, description="Minutes of active movement")
    calories_burned_kcal: float | None = Field(None, description="Estimated calories burned (kcal)")

    # Sleep metrics
    sleep_duration_hrs: float | None = Field(None, description="Total sleep duration (hours)")
    sleep_quality_score: int | None = Field(None, description="Sleep quality score (0–100)")
    deep_sleep_pct: float | None = Field(None, description="Percentage of sleep in deep stage")

    # Blood oxygen
    spo2_avg_pct: float | None = Field(None, description="Average SpO2 percentage")


class WearableSeriesOut(BaseModel):
    """Time-series of wearable data for a patient."""

    model_config = ConfigDict(from_attributes=True)

    patient_id: str = Field(..., description="Patient identifier")
    days: list[WearableDayOut] = Field(
        default_factory=list,
        description="Daily measurements ordered descending by date",
    )
