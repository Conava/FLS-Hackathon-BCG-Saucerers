"""AI observability and envelope schemas.

``AIMeta`` carries the non-PHI observability fields logged with every LLM
call: model name, prompt name, request ID, and token/latency counters.

``AIResponseEnvelope`` is a mixin base class that injects ``disclaimer`` and
``ai_meta`` into any AI-powered response schema.  All AI response schemas
inherit from ``AIResponseEnvelope`` (in addition to ``BaseModel`` via MRO or
via composition) so the OpenAPI spec always includes the wellness disclaimer
and the AI observability payload.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

#: Wellness-framed disclaimer that must appear on every AI response.
AI_DISCLAIMER = "This is wellness guidance, not medical advice."


class AIMeta(BaseModel):
    """Non-PHI observability metadata for a single LLM call.

    Logged as a structured JSON line alongside every AI response.
    Contains no patient-identifiable information — only model-level signals.
    """

    model_config = ConfigDict(from_attributes=True)

    model: str = Field(..., description="LLM model identifier, e.g. 'gemini-2.5-flash'")
    prompt_name: str = Field(..., description="Prompt template name, e.g. 'coach'")
    request_id: str = Field(..., description="Unique request identifier for log correlation")
    token_in: int = Field(..., description="Input token count (prompt)")
    token_out: int = Field(..., description="Output token count (completion)")
    latency_ms: int = Field(..., description="End-to-end LLM call latency in milliseconds")


class AIResponseEnvelope(BaseModel):
    """Mixin base class that injects wellness disclaimer and AI metadata.

    Every AI-powered response schema inherits from this class so the OpenAPI
    spec consistently surfaces the mandatory wellness framing and the
    observability payload without repeating field definitions.

    Subclasses should include ``model_config = ConfigDict(from_attributes=True)``
    unless they explicitly require different serialisation behaviour.
    """

    model_config = ConfigDict(from_attributes=True)

    disclaimer: str = Field(
        default=AI_DISCLAIMER,
        description="Mandatory wellness framing — this guidance is not medical advice.",
    )
    ai_meta: AIMeta = Field(..., description="Non-PHI observability metadata for the LLM call")
