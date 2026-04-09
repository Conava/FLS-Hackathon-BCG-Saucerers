"""Insights and risk-flag response DTOs.

Wellness framing is enforced: field names use ``risk_flags``, ``signals``,
and ``prevention_signals``. No diagnostic verbs (diagnose, treat, cure, etc.)
appear in any field name.

``InsightOut.severity`` is constrained to ``low | moderate | high`` — mirroring
the values the vitality engine emits and matching the mockup's chip colours.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: Wellness-framed disclaimer included in every insight response.
DISCLAIMER = "Wellness signal, not medical advice."


class InsightOut(BaseModel):
    """A single wellness insight derived from patient data.

    Fields follow wellness framing: ``signals`` describes what was observed;
    ``prevention_signals`` lists actionable lifestyle suggestions;
    ``kind`` categorises the insight (e.g. 'lipid', 'sleep', 'activity').
    """

    model_config = ConfigDict(from_attributes=True)

    kind: str = Field(
        ...,
        description="Insight category, e.g. 'lipid', 'sleep', 'activity', 'cardiac'",
    )
    severity: Literal["low", "moderate", "high"] = Field(
        ...,
        description="Signal severity level: low | moderate | high",
    )
    message: str = Field(
        ...,
        description="Human-readable wellness message (wellness-framed, no diagnostic verbs)",
    )
    signals: list[str] = Field(
        default_factory=list,
        description="Supporting data points that triggered this insight",
    )
    prevention_signals: list[str] = Field(
        default_factory=list,
        description="Actionable wellness suggestions",
    )
    disclaimer: str = Field(
        default=DISCLAIMER,
        description="Mandatory wellness framing statement",
    )


class InsightsListOut(BaseModel):
    """Aggregated insights response for a patient."""

    model_config = ConfigDict(from_attributes=True)

    patient_id: str = Field(..., description="Patient the insights belong to")
    insights: list[InsightOut] = Field(
        default_factory=list,
        description="Ordered list of wellness insights (highest severity first)",
    )
    risk_flags: list[str] = Field(
        default_factory=list,
        description="Top-level wellness signal identifiers",
    )
    signals: list[str] = Field(
        default_factory=list,
        description="Aggregated supporting observations across all insights",
    )
    prevention_signals: list[str] = Field(
        default_factory=list,
        description="Aggregated actionable wellness suggestions across all insights",
    )
