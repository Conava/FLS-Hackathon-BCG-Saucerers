"""Meal log request/response DTOs.

``MealAnalysis`` is the structured LLM output from the Meal Vision endpoint.
It is also stored in the ``MealLog`` table's ``analysis`` JSONB column.

``MealLogUploadResponse`` extends ``AIResponseEnvelope`` so it always carries
the wellness disclaimer and AI observability metadata.

``MealLogOut`` / ``MealLogListOut`` are the read-path response schemas.
"""

from __future__ import annotations

import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ai_common import AIResponseEnvelope


class MealAnalysis(BaseModel):
    """Structured output from the Meal Vision LLM call.

    Mirrors the contract in docs/06-ai-layer.md:
    - ``classification``: plain-English meal description
    - ``macros``: dictionary with kcal, protein_g, carbs_g, fat_g keys
    - ``longevity_swap``: one-line swap suggestion; empty string if already optimal
    """

    model_config = ConfigDict(from_attributes=True)

    classification: str = Field(
        ...,
        description="Plain-English meal description, e.g. 'grilled salmon, white rice, broccoli'",
    )
    macros: dict[str, Any] = Field(
        ...,
        description=(
            "Macro nutrient breakdown. Expected keys: kcal (int), "
            "protein_g (float), carbs_g (float), fat_g (float). "
            "Optional: fiber_g (float)."
        ),
    )
    longevity_swap: str = Field(
        ...,
        description=(
            "One-line longevity swap suggestion, e.g. "
            "'Replace white rice with quinoa for more protein and fibre.' "
            "Empty string if the meal is already well-optimised."
        ),
    )
    swap_rationale: str = Field(
        ...,
        description="One line explaining the longevity benefit of the swap. Empty string if longevity_swap is empty.",
    )


class MealLogUploadResponse(AIResponseEnvelope):
    """Response from the meal photo upload endpoint.

    Inherits ``disclaimer`` and ``ai_meta`` from ``AIResponseEnvelope``.
    Returns the persisted meal log ID, the photo storage URI, and the analysis.
    """

    meal_log_id: int = Field(..., description="Primary key of the persisted MealLog row")
    photo_uri: str = Field(
        ...,
        description="Storage URI for the uploaded photo (local:// or gs://)",
    )
    analysis: MealAnalysis = Field(
        ...,
        description="Structured macro analysis returned by the Meal Vision model",
    )


class MealLogOut(BaseModel):
    """API response schema for a single persisted meal log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Meal log primary key")
    patient_id: str = Field(..., description="Patient this meal log belongs to")
    logged_at: datetime.datetime = Field(
        ...,
        description="Timestamp when the meal was logged (naive UTC)",
    )
    photo_uri: str = Field(
        ...,
        description="Storage URI for the meal photo",
    )
    analysis: MealAnalysis = Field(
        ...,
        description="Structured macro analysis from the Meal Vision model",
    )
    notes: str | None = Field(
        None,
        description="Optional free-text notes from the patient",
    )


class ManualMealLogIn(BaseModel):
    """Request body for the manual meal-log endpoint (no photo, no LLM call).

    The caller supplies all macro values directly.  The endpoint persists a
    ``MealLog`` row with a ``manual://<uuid>`` sentinel ``photo_uri`` so the
    existing history list can render manual entries without breaking.
    """

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(
        ...,
        description="Plain-English meal name, e.g. 'Grilled chicken salad'",
    )
    kcal: int = Field(..., ge=0, description="Total kilocalories")
    protein_g: float = Field(..., ge=0.0, description="Protein in grams")
    carbs_g: float = Field(..., ge=0.0, description="Carbohydrates in grams")
    fat_g: float = Field(..., ge=0.0, description="Fat in grams")
    fiber_g: float = Field(default=0.0, ge=0.0, description="Dietary fibre in grams")
    notes: str | None = Field(None, description="Optional free-text notes from the patient")


class MealLogListOut(BaseModel):
    """API response schema for a list of meal log entries."""

    model_config = ConfigDict(from_attributes=True)

    patient_id: str = Field(..., description="Patient the meal logs belong to")
    logs: list[MealLogOut] = Field(
        default_factory=list,
        description="Meal log entries ordered by logged_at descending",
    )
