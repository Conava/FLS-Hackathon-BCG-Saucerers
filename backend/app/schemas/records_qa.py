"""Records Q&A request/response DTOs.

``RecordsQARequest`` is the inbound payload for
``POST /v1/patients/{pid}/records/qa``.

``RecordsQAResponse`` extends ``AIResponseEnvelope`` so it always carries
the wellness disclaimer and AI observability metadata alongside the answer
and citation list.

Citations reference ``EHRRecord.id`` values so the client can render
clickable chip links back to source records.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ai_common import AIResponseEnvelope


class RecordsQARequest(BaseModel):
    """Inbound payload for the EHR records Q&A endpoint."""

    model_config = ConfigDict(from_attributes=True)

    question: str = Field(
        ...,
        description="The patient's natural-language question about their records",
    )


class Citation(BaseModel):
    """A single EHR record citation returned with a Q&A answer.

    ``snippet`` is a short excerpt from the source record (≤200 chars)
    that substantiates the answer.  The client renders this in a citation chip.
    """

    model_config = ConfigDict(from_attributes=True)

    record_id: int = Field(..., description="Primary key of the EHRRecord that was cited")
    snippet: str = Field(
        ...,
        description="Short excerpt from the source record (≤200 chars)",
    )


class RecordsQAResponse(AIResponseEnvelope):
    """Response from the EHR records Q&A endpoint.

    Inherits ``disclaimer`` and ``ai_meta`` from ``AIResponseEnvelope``.
    The answer is strictly grounded in the retrieved records — no hallucination.
    If no relevant record exists, the model must answer "I don't have that information."
    """

    answer: str = Field(
        ...,
        description="The model's answer, strictly grounded in retrieved EHR records",
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="EHR records that substantiate the answer, ordered by relevance",
    )
