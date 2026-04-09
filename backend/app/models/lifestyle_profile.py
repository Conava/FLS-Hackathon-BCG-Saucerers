"""SQLModel entity: LifestyleProfile.

One row per patient — the latest lifestyle survey response. Column names match
lifestyle_survey.csv headers so the CSV adapter can map by name.

patient_id is both the primary key and a FK to patient.patient_id, enforcing
the one-to-one relationship. No separate index needed (PK index covers it).
"""

from __future__ import annotations

from datetime import date

from sqlmodel import Field, SQLModel


class LifestyleProfile(SQLModel, table=True):
    """Patient lifestyle survey response (single-row per patient, latest only)."""

    __tablename__ = "lifestyle_profile"

    patient_id: str = Field(foreign_key="patient.patient_id", primary_key=True)

    # Date the survey was completed
    survey_date: date

    # Substance use
    smoking_status: str | None = Field(default=None)
    alcohol_units_weekly: float | None = Field(default=None)

    # Nutrition
    diet_quality_score: int | None = Field(default=None)          # self-rated 1–10
    fruit_veg_servings_daily: float | None = Field(default=None)
    meal_frequency_daily: int | None = Field(default=None)
    water_glasses_daily: int | None = Field(default=None)

    # Activity & sedentary behaviour
    exercise_sessions_weekly: int | None = Field(default=None)
    sedentary_hrs_day: float | None = Field(default=None)

    # Psychological wellbeing
    stress_level: int | None = Field(default=None)                # 1–10
    sleep_satisfaction: int | None = Field(default=None)          # 1–10
    mental_wellbeing_who5: int | None = Field(default=None)       # WHO-5 score 0–100
    self_rated_health: int | None = Field(default=None)           # 1–10
