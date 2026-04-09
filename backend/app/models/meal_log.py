"""SQLModel entity: MealLog.

Records a meal-photo analysis event. A photo is uploaded, stored via the
PhotoStorage adapter (local-fs or GCS), and then analyzed by Gemini Vision.
The resulting macros (protein/carbs/fat/fiber) and the longevity-optimized swap
suggestion are persisted here alongside the photo URI.

The photo_uri field stores the storage-adapter URI (e.g.
"local://var/photos/PT0001/<uuid>.jpg" or "gs://bucket/PT0001/<uuid>.jpg")
so GDPR deletion can use the adapter to remove the file.
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import Column, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime.datetime:
    """Return current UTC time as timezone-naive datetime (CLAUDE.md pattern)."""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


class MealLog(SQLModel, table=True):
    """A single meal-photo analysis result for a patient."""

    __tablename__ = "meal_log"

    # Named index on patient_id — do NOT add index=True to Field below.
    __table_args__ = (Index("ix_meal_log_patient_id", "patient_id"),)

    id: int | None = Field(default=None, primary_key=True)

    # Patient isolation boundary — indexed via __table_args__
    patient_id: str = Field(foreign_key="patient.patient_id")

    # Storage-adapter URI — used for retrieval and GDPR deletion
    photo_uri: str

    # Macro breakdown from Gemini vision — nullable until analysis completes
    # Structure: {"protein_g": float, "carbs_g": float, "fat_g": float, "fiber_g": float,
    #              "calories_kcal": float, "description": str}
    macros: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )

    # One-line wellness-framed swap suggestion (e.g. "Swap white rice for lentils")
    longevity_swap: str | None = Field(default=None)

    # Timestamp of Gemini analysis (naive UTC)
    analyzed_at: datetime.datetime
