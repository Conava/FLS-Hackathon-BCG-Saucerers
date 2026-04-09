"""Protocol generator request/response DTOs.

``GeneratedAction`` and ``GeneratedProtocol`` are the structured output schemas
validated against the LLM's JSON response before persisting to the database.
They mirror the contracts defined in docs/06-ai-layer.md.

``ProtocolOut`` / ``ProtocolActionOut`` are the API response schemas for
reading a persisted protocol.

``CompleteActionRequest`` / ``CompleteActionResponse`` are the inbound and
outbound DTOs for marking a protocol action as completed.
"""

from __future__ import annotations

import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GeneratedAction(BaseModel):
    """A single protocol action as returned by the LLM structured output.

    Validated by Pydantic before any DB write — if the model violates
    ``category`` or ``dimension`` constraints the call is rejected.
    """

    model_config = ConfigDict(from_attributes=True)

    category: Literal["movement", "sleep", "nutrition", "mind", "supplement"] = Field(
        ...,
        description="Action category: movement | sleep | nutrition | mind | supplement",
    )
    title: str = Field(
        ...,
        description="Short human-readable action title shown on the Today card",
    )
    target: str = Field(
        ...,
        description="Measurable target, e.g. '30 minutes daily' or '10pm bedtime'",
    )
    rationale: str = Field(
        ...,
        description="One-line rationale shown below the action on the Today screen",
    )
    dimension: Literal[
        "biological_age", "sleep_recovery", "cardio_fitness", "lifestyle_behavioral"
    ] = Field(
        ...,
        description=(
            "Longevity dimension this action targets: "
            "biological_age | sleep_recovery | cardio_fitness | lifestyle_behavioral"
        ),
    )


class GeneratedProtocol(BaseModel):
    """The full structured protocol as returned by the LLM.

    ``actions`` must contain 3–7 items (enforced at service layer).
    This schema is used as the ``response_schema`` parameter to ``LLMProvider.generate``.
    """

    model_config = ConfigDict(from_attributes=True)

    rationale: str = Field(
        ...,
        description=(
            "One paragraph shown at the top of Today's protocol explaining "
            "the week's focus areas and why they were chosen"
        ),
    )
    actions: list[GeneratedAction] = Field(
        ...,
        description="List of 3–7 protocol actions (constraint enforced at service layer)",
    )


class ProtocolActionOut(BaseModel):
    """API response schema for a single persisted protocol action."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Protocol action primary key")
    protocol_id: int = Field(..., description="Parent protocol primary key")
    category: str = Field(..., description="Action category")
    title: str = Field(..., description="Action title")
    target: str | None = Field(
        default=None,
        description="Measurable target (optional — model stores this as target_value)",
    )
    rationale: str | None = Field(default=None, description="One-line rationale")
    dimension: str | None = Field(
        default=None,
        description="Longevity dimension (optional — not stored on ProtocolAction model)",
    )
    completed_today: bool = Field(
        default=False,
        description="Whether the action has been completed today",
    )
    streak_days: int = Field(
        default=0,
        description="Consecutive days this action has been completed",
    )
    sort_order: int | None = Field(
        default=None,
        description="Explicit display order (1-indexed); NULL rows sort last",
    )
    skipped_today: bool = Field(
        default=False,
        description="Whether the action has been skipped today",
    )
    skip_reason: str | None = Field(
        default=None,
        description="Human-readable reason provided when skipping today",
    )


class ProtocolOut(BaseModel):
    """API response schema for a full persisted protocol with its actions."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Protocol primary key")
    patient_id: str = Field(..., description="Patient this protocol belongs to")
    created_at: datetime.datetime = Field(
        ...,
        description="Timestamp when the protocol was generated (maps to Protocol.created_at)",
    )
    rationale: str | None = Field(
        default=None,
        description="Protocol-level rationale paragraph (optional — not stored on Protocol model)",
    )
    actions: list[ProtocolActionOut] = Field(
        default_factory=list,
        description="Ordered list of protocol actions",
    )


class CompleteActionRequest(BaseModel):
    """Inbound payload for marking a protocol action as completed."""

    model_config = ConfigDict(from_attributes=True)

    action_id: int = Field(..., description="Primary key of the ProtocolAction to complete")


class CompleteActionResponse(BaseModel):
    """Response after marking a protocol action as completed."""

    model_config = ConfigDict(from_attributes=True)

    action_id: int = Field(..., description="Primary key of the completed action")
    streak_days: int = Field(
        ...,
        description="Updated consecutive-days streak after this completion",
    )
    completed_at: datetime.datetime = Field(
        ...,
        description="Timestamp the action was marked complete",
    )


class SkipActionRequest(BaseModel):
    """Inbound payload for skipping a protocol action today."""

    model_config = ConfigDict(from_attributes=True)

    action_id: int = Field(..., description="Primary key of the ProtocolAction to skip")
    reason: str = Field(..., description="Human-readable reason for skipping today")


class ReorderRequest(BaseModel):
    """Inbound payload for reordering protocol actions.

    ``action_ids`` must list ALL action ids for the patient's active protocol
    in the desired display order.  The endpoint assigns sort_order = position
    (1-indexed) for each entry.
    """

    model_config = ConfigDict(from_attributes=True)

    action_ids: list[int] = Field(
        ...,
        description="Action ids in the desired display order (all actions must be included)",
    )
