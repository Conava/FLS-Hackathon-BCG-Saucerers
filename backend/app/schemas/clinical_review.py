"""Clinical review request/response DTOs.

``ClinicalReviewIn`` is the inbound payload for flagging a patient record
for clinical review.

``ClinicalReviewOut`` is the response for a persisted clinical review row.

These are stubs — the MVP does not route to a real clinician workflow.
A ``ClinicalReview`` row is persisted and the status is ``pending`` until
a future integration updates it.

Wellness framing: the ``notes`` field uses patient-provided free text;
the API consumer is responsible for not including diagnostic language.
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field


class ClinicalReviewIn(BaseModel):
    """Inbound payload for ``POST /v1/patients/{pid}/clinical-review``."""

    model_config = ConfigDict(from_attributes=True)

    patient_id: str = Field(..., description="Patient flagged for review")
    notes: str = Field(
        ...,
        description="Free-text notes describing the wellness concern",
    )


class ClinicalReviewOut(BaseModel):
    """API response schema for a persisted clinical review row."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Clinical review primary key")
    patient_id: str = Field(..., description="Patient the review belongs to")
    notes: str = Field(..., description="Wellness concern notes")
    status: str = Field(
        ...,
        description="Review status: 'pending' | 'in_review' | 'resolved'",
    )
    created_at: datetime.datetime = Field(
        ...,
        description="Timestamp when the review was created (naive UTC)",
    )
