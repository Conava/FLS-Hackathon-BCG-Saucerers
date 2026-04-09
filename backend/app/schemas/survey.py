"""Survey request/response DTOs.

``SurveyKind`` identifies which survey variant is being submitted.
The three variants share the same endpoint — the ``kind`` field routes
persistence and any downstream ``LifestyleProfile`` field updates.

``SurveySubmitRequest`` is the inbound payload.
``SurveyResponseOut`` is the response for a single persisted survey.
``SurveyHistoryOut`` wraps the list of surveys returned by the history endpoint.
"""

from __future__ import annotations

import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SurveyKind(StrEnum):
    """Survey variant discriminator.

    - ``onboarding``: filled once when the patient first joins
    - ``weekly``: short check-in submitted each week
    - ``quarterly``: deeper review submitted every three months
    """

    onboarding = "onboarding"
    weekly = "weekly"
    quarterly = "quarterly"


class SurveySubmitRequest(BaseModel):
    """Inbound payload for ``POST /v1/patients/{pid}/survey``."""

    model_config = ConfigDict(from_attributes=True)

    kind: SurveyKind = Field(
        ...,
        description="Survey variant: onboarding | weekly | quarterly",
    )
    answers: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Survey answers as key-value pairs. "
            "Keys are LifestyleProfile column names where applicable."
        ),
    )


class SurveyResponseOut(BaseModel):
    """API response schema for a single persisted survey submission."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Survey response primary key")
    patient_id: str = Field(..., description="Patient the survey belongs to")
    kind: SurveyKind = Field(..., description="Survey variant")
    submitted_at: datetime.datetime = Field(
        ...,
        description="Timestamp when the survey was submitted (naive UTC)",
    )
    answers: dict[str, Any] = Field(
        default_factory=dict,
        description="The submitted answers",
    )


class SurveyHistoryOut(BaseModel):
    """API response schema for the list of a patient's survey submissions."""

    model_config = ConfigDict(from_attributes=True)

    patient_id: str = Field(..., description="Patient the history belongs to")
    responses: list[SurveyResponseOut] = Field(
        default_factory=list,
        description="Survey responses ordered by submitted_at descending",
    )
