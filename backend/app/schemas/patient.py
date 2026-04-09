"""Patient profile response DTO.

This module defines the Pydantic v2 response schema for patient profile data.
It is intentionally separate from the SQLModel table definition — DTOs are
pure serialisation contracts; table models are persistence concerns.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PatientProfileOut(BaseModel):
    """Response schema for a patient's demographic profile.

    All field names follow wellness framing: no diagnostic verbs.
    Optional fields are ``None`` when data is unavailable (documented gap
    in the CSV source — no date_of_birth, some anthropometric values absent).
    """

    model_config = ConfigDict(from_attributes=True)

    patient_id: str = Field(..., description="Unique patient identifier, e.g. PT0282")
    name: str = Field(..., description="Patient display name")
    age: int = Field(..., description="Age in years")
    country: str = Field(..., description="Country of residence (ISO-3166 alpha-2 or full name)")
    sex: str | None = Field(None, description="Biological sex (male/female/other)")
    bmi: float | None = Field(None, description="Body Mass Index (kg/m²)")
    smoking_status: str | None = Field(None, description="Smoking status (never/former/current)")
    height_cm: float | None = Field(None, description="Height in centimetres")
    weight_kg: float | None = Field(None, description="Weight in kilograms")
