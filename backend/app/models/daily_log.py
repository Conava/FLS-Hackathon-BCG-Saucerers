"""SQLModel entity: DailyLog.

Quick-log record for daily self-tracking data: mood, workout minutes, sleep
hours, water intake, and alcohol units. Optionally linked to a specific
ProtocolAction (when the log event was triggered by tapping a protocol action
on the Today tab).

One row per log event. Multiple rows per day are allowed (e.g. separate mood
and workout logs). Callers should aggregate by date when computing streak stats.
"""

from __future__ import annotations

import datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime.datetime:
    """Return current UTC time as timezone-naive datetime (CLAUDE.md pattern)."""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


class DailyLog(SQLModel, table=True):
    """A single quick-log event for a patient.

    Fields are individually optional — a log may record only mood, or only
    a workout, etc. The protocol_action_id FK is set when the log was triggered
    by completing a protocol action.
    """

    __tablename__ = "daily_log"

    # Named index on patient_id — do NOT add index=True to Field below.
    __table_args__ = (Index("ix_daily_log_patient_id", "patient_id"),)

    id: int | None = Field(default=None, primary_key=True)

    # Patient isolation boundary — indexed via __table_args__
    patient_id: str = Field(foreign_key="patient.patient_id")

    # When the log was recorded (naive UTC)
    logged_at: datetime.datetime

    # Quick-log fields — all optional; log what you have
    mood: int | None = Field(default=None)  # 1–5 subjective mood scale
    workout_minutes: int | None = Field(default=None)
    sleep_hours: float | None = Field(default=None)
    water_ml: int | None = Field(default=None)
    alcohol_units: float | None = Field(default=None)

    # Structured sleep metadata
    sleep_quality: int | None = Field(default=None)  # 1–5 Likert scale

    # Structured workout metadata
    workout_type: str | None = Field(default=None)  # walk/run/bike/strength/yoga/other
    workout_intensity: str | None = Field(default=None)  # low/med/high

    # Optional FK — set when this log corresponds to completing a protocol action
    protocol_action_id: int | None = Field(
        default=None, foreign_key="protocol_action.id"
    )
