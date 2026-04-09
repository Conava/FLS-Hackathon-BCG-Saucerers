"""SQLModel entity: WearableDay.

One row per (patient_id, date) — a daily aggregate of wearable telemetry.
Column names match the wearable_telemetry_1.csv headers exactly so the CSV
adapter can map fields by name without a translation layer.

Composite primary key: (patient_id, date) — prevents duplicate inserts for
the same patient on the same day; also serves as the natural upsert key.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


class WearableDay(SQLModel, table=True):
    """Daily wearable telemetry aggregate for a patient."""

    __tablename__ = "wearable_day"

    # Named index on patient_id for per-patient queries.
    # Single source of truth: __table_args__ provides the canonical name.
    # Do NOT add index=True to the Field below — that creates a duplicate index
    # which causes Postgres to fail with "relation already exists" at create_all().
    __table_args__ = (Index("ix_wearable_day_patient_id", "patient_id"),)

    # Composite PK — (patient_id, date) is the natural unique key
    # patient_id is indexed via __table_args__ above — no index=True here
    patient_id: str = Field(
        foreign_key="patient.patient_id",
        primary_key=True,
    )
    date: dt.date = Field(primary_key=True)

    # --- Heart metrics ---
    resting_hr_bpm: int | None = Field(default=None)
    hrv_rmssd_ms: float | None = Field(default=None)

    # --- Activity ---
    steps: int | None = Field(default=None)
    active_minutes: int | None = Field(default=None)
    calories_burned_kcal: int | None = Field(default=None)

    # --- Sleep ---
    sleep_duration_hrs: float | None = Field(default=None)
    sleep_quality_score: float | None = Field(default=None)
    deep_sleep_pct: float | None = Field(default=None)

    # --- Oxygen saturation ---
    spo2_avg_pct: float | None = Field(default=None)
