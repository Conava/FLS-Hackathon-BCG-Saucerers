"""Vitality score response DTOs.

``VitalityOut`` is the primary response schema for the heuristic wellness score.
It intentionally uses wellness framing — no diagnostic verbs in field names.

Subscore keys are fixed: ``sleep``, ``activity``, ``metabolic``, ``cardio``,
``lifestyle`` — matching the vitality engine constants defined in
``app/services/vitality_engine.py``.
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field

#: Wellness-framed disclaimer included in every vitality response.
DISCLAIMER = "Wellness signal, not medical advice."


class TrendPoint(BaseModel):
    """A single data point in the 7-day vitality trend."""

    model_config = ConfigDict(from_attributes=True)

    date: datetime.date = Field(..., description="Calendar date for this score")
    score: float = Field(..., description="Computed vitality score (0–100) for the day")


class VitalityOut(BaseModel):
    """Response schema for the heuristic vitality score.

    Includes the composite score, domain-level subscores, a 7-day trend,
    risk flags (wellness-framed — no diagnostic verbs), and a mandatory
    disclaimer that this is a wellness signal, not a medical assessment.
    """

    model_config = ConfigDict(from_attributes=True)

    score: float = Field(..., description="Composite wellness score (0–100)")
    subscores: dict[str, float] = Field(
        ...,
        description=(
            "Domain subscores keyed by: sleep, activity, metabolic, cardio, lifestyle"
        ),
    )
    trend: list[TrendPoint] = Field(
        default_factory=list,
        description="Per-day score over the last N days (typically 7)",
    )
    computed_at: datetime.datetime = Field(..., description="Timestamp when score was computed")
    risk_flags: list[str] = Field(
        default_factory=list,
        description="Wellness-framed signal identifiers, e.g. 'elevated_ldl'",
    )
    disclaimer: str = Field(
        default=DISCLAIMER,
        description="Mandatory wellness framing statement",
    )
