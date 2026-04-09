"""SQLModel entity: Patient.

Unified patient identity record. All child tables reference patient_id as a
foreign key, ensuring hard isolation at the SQL level (GDPR + RAG safety).

Note: date_of_birth is intentionally absent — the CSV datasets provide age
only, not date of birth. This is a documented data gap for this slice.
"""

from __future__ import annotations

import datetime

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.UTC)


class Patient(SQLModel, table=True):
    """Unified patient identity.

    patient_id is a string identifier from the source system (e.g. "PT0001").
    All analytics, AI calls, and UI screens consume this model.
    """

    __tablename__ = "patient"

    patient_id: str = Field(primary_key=True)
    name: str
    age: int
    sex: str
    country: str

    # Biometric fields — optional because some source rows may omit them
    height_cm: float | None = Field(default=None)
    weight_kg: float | None = Field(default=None)
    bmi: float | None = Field(default=None)

    # Lifestyle summary fields copied from EHR CSV row for quick access
    # (the LifestyleProfile table holds the full survey breakdown)
    smoking_status: str | None = Field(default=None)
    alcohol_units_weekly: float | None = Field(default=None)

    # Audit timestamps
    created_at: datetime.datetime = Field(default_factory=_utcnow)
    updated_at: datetime.datetime = Field(default_factory=_utcnow)
