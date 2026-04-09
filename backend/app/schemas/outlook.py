"""Vitality Outlook request/response DTOs.

``OutlookOut`` is the read-path response for ``GET /v1/patients/{pid}/outlook``.
It reflects the persisted ``VitalityOutlook`` row.

``OutlookNarratorRequest`` / ``OutlookNarratorResponse`` are the inbound and
AI-envelope outbound schemas for the LLM-driven outlook narration endpoint.

``FutureSelfRequest`` / ``FutureSelfResponse`` are the inbound and
AI-envelope outbound schemas for the Future Self Simulator endpoint.
Both AI response schemas inherit from ``AIResponseEnvelope`` so they always
include the wellness disclaimer and AI metadata.
"""

from __future__ import annotations

import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ai_common import AIResponseEnvelope


class OutlookOut(BaseModel):
    """API response schema for a persisted VitalityOutlook entry.

    ``projected_score`` is the streak-math extrapolation of the current
    vitality trajectory over ``horizon_months``.
    ``narrative`` is the one-sentence LLM narration cached from the last
    Outlook Narrator call.
    """

    model_config = ConfigDict(from_attributes=True)

    horizon_months: int = Field(
        ...,
        description="Forecast horizon in calendar months",
    )
    projected_score: float = Field(
        ...,
        description="Projected vitality score at the horizon (0–100)",
    )
    narrative: str = Field(
        ...,
        description="One-sentence wellness-framed narrative of the outlook trajectory",
    )
    computed_at: datetime.datetime = Field(
        ...,
        description="Timestamp when this outlook was computed (naive UTC)",
    )


class OutlookNarratorRequest(BaseModel):
    """Inbound payload for the Outlook Narrator AI endpoint."""

    model_config = ConfigDict(from_attributes=True)

    patient_id: str = Field(..., description="Patient to narrate the outlook for")
    horizon_months: int = Field(
        default=6,
        ge=1,
        le=24,
        description="Forecast horizon in calendar months (1–24)",
    )
    top_drivers: list[str] = Field(
        default_factory=list,
        description="Top 1–2 vitality driver categories to mention in the narrative",
    )


class OutlookNarratorResponse(AIResponseEnvelope):
    """Response from the Outlook Narrator endpoint.

    Inherits ``disclaimer`` and ``ai_meta`` from ``AIResponseEnvelope``.
    ``narrative`` is a single sentence summarising the outlook trajectory
    with wellness framing — no diagnostic language.
    """

    narrative: str = Field(
        ...,
        description=(
            "One wellness-framed sentence, e.g. "
            "'Hold your streak and your Outlook reaches 74 by October — "
            "mostly from sleep consistency.'"
        ),
    )


class FutureSelfRequest(BaseModel):
    """Inbound payload for the Future Self Simulator endpoint.

    ``sliders`` maps lifestyle dimension names to adjustment values
    (e.g. ``{\"sleep_improvement\": 2, \"exercise_frequency\": 4}``).
    The service uses these to project a modified bio-age and trajectory.
    """

    model_config = ConfigDict(from_attributes=True)

    patient_id: str = Field(..., description="Patient to project the future self for")
    sliders: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Slider adjustments keyed by lifestyle dimension. "
            "Values are numeric adjustment amounts."
        ),
    )


class FutureSelfResponse(AIResponseEnvelope):
    """Response from the Future Self Simulator endpoint.

    Inherits ``disclaimer`` and ``ai_meta`` from ``AIResponseEnvelope``.
    ``bio_age`` is the projected biological age given the slider adjustments.
    ``narrative`` is a paragraph comparing the current and improved trajectories.
    """

    bio_age: int = Field(
        ...,
        description="Projected biological age (years) given the slider-adjusted lifestyle",
    )
    narrative: str = Field(
        ...,
        description=(
            "Wellness-framed paragraph comparing current trajectory vs improved, "
            "e.g. 'Here's you at 70 on current trajectory vs improved'"
        ),
    )
