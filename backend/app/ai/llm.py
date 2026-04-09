"""LLM abstraction layer.

Defines the ``LLMProvider`` structural Protocol and ships two implementations:

* ``FakeLLMProvider`` — fully deterministic, no network, safe for unit tests.
* ``GeminiProvider`` — wraps the ``google-genai`` SDK via Vertex AI.

Both are runtime-checkable so ``isinstance(p, LLMProvider)`` works.

Factory::

    from app.ai.llm import get_llm_provider
    llm = get_llm_provider(settings)

Stack contract (see docs/09-ai-assist-playbook.md):
    - Use ``from google import genai`` — NOT ``google-generativeai`` or
      ``vertexai.generative_models``.
    - ``genai.Client(vertexai=True, project=..., location=...)``
    - Structured output: ``GenerateContentConfig(response_mime_type=..., response_schema=...)``
"""
from __future__ import annotations

import hashlib
import random
from typing import TYPE_CHECKING, AsyncIterator, runtime_checkable

from typing import Protocol

from pydantic import BaseModel

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# google-genai import — safe at module level; tests monkeypatch this name
# ---------------------------------------------------------------------------
from google import genai  # noqa: E402  (must be google-genai, not google-generativeai)


# ---------------------------------------------------------------------------
# Protocol definition
# ---------------------------------------------------------------------------


@runtime_checkable
class LLMProvider(Protocol):
    """Structural protocol for LLM providers.

    Any class that implements all four async methods satisfies this protocol.
    The ``@runtime_checkable`` decorator enables ``isinstance()`` checks.

    All methods are *async* — callers must ``await`` or ``async for`` them.
    """

    async def generate(
        self,
        *,
        system: str,
        user: str,
        model: str,
        response_schema: type[BaseModel] | None = None,
    ) -> str | dict:
        """Generate a text (or structured-JSON) response.

        Args:
            system: System-level instruction prompt.
            user: User message / query.
            model: Model identifier, e.g. ``"gemini-2.5-flash"``.
            response_schema: Optional Pydantic ``BaseModel`` subclass.  When
                provided the response MUST be a ``dict`` conforming to that
                schema.  When ``None`` the response is a plain ``str``.

        Returns:
            ``str`` when ``response_schema`` is ``None``; ``dict`` otherwise.
        """
        ...

    def generate_stream(
        self,
        *,
        system: str,
        user: str,
        model: str,
    ) -> "AsyncIterator[str]":
        """Return an async iterator that streams text tokens.

        This is a regular (non-async) method that returns an ``AsyncIterator``.
        Callers use ``async for`` on the returned object.

        Args:
            system: System-level instruction prompt.
            user: User message / query.
            model: Model identifier.

        Returns:
            An async iterator that yields string tokens in order.
        """
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts into dense vector representations.

        Args:
            texts: Strings to embed.

        Returns:
            A list of float vectors, one per input text.  Each vector has
            the model-specific dimensionality (768 for ``text-embedding-004``).
        """
        ...

    async def generate_vision(
        self,
        *,
        system: str,
        prompt: str,
        image_bytes: bytes,
        model: str,
        response_schema: type[BaseModel],
    ) -> dict:
        """Analyse an image and return structured JSON.

        Args:
            system: System-level instruction prompt.
            prompt: User-side textual instruction about the image.
            image_bytes: Raw image data (JPEG or PNG).
            model: Model identifier.
            response_schema: Pydantic ``BaseModel`` subclass describing the
                expected JSON output shape.

        Returns:
            A ``dict`` conforming to ``response_schema``'s JSON schema.
        """
        ...


# ---------------------------------------------------------------------------
# FakeLLMProvider — deterministic stub
# ---------------------------------------------------------------------------

_DISCLAIMER = "This is wellness guidance, not medical advice."

_STREAM_TOKENS = ["Here", " is", " a", " reply", "."]

_FAKE_VISION: dict = {
    "classification": "grilled salmon, white rice, broccoli",
    "macros": {
        "kcal": 520,
        "protein_g": 42,
        "carbs_g": 48,
        "fat_g": 14,
        "fiber_g": 6,
    },
    "longevity_swap": "Swap white rice for brown rice or quinoa for more fibre.",
    "swap_rationale": "Higher fibre intake is associated with reduced all-cause mortality.",
}


def _hash_inputs(system: str, user: str) -> int:
    """Return a stable integer hash derived from system and user strings.

    Uses MD5 (via hashlib) for cross-platform determinism — Python's built-in
    ``hash()`` is randomised per-process (PYTHONHASHSEED) and must NOT be used
    for reproducible outputs.
    """
    combined = f"{system}\x00{user}"
    return int(hashlib.md5(combined.encode()).hexdigest(), 16)


class FakeLLMProvider:
    """Deterministic LLM stub for testing and local development.

    Behaviour is keyed on the hash of ``(system, user)`` so the same inputs
    always return the same output, enabling snapshot-style assertions without
    live network calls.

    * ``generate`` — returns a short sentence + the wellness disclaimer (text),
      or a ``dict`` with schema-defaults (structured).
    * ``generate_stream`` — yields the fixed token sequence ``_STREAM_TOKENS``.
    * ``embed`` — returns 768-d vectors derived from ``random.Random(hash(text))``,
      values in ``[-1, 1]``.
    * ``generate_vision`` — returns ``_FAKE_VISION``.
    """

    async def generate(
        self,
        *,
        system: str,
        user: str,
        model: str,
        response_schema: type[BaseModel] | None = None,
    ) -> str | dict:
        """Return deterministic text or structured response.

        When ``response_schema`` is provided returns a ``dict`` built from the
        schema's default-value instantiation.  Otherwise returns a short text
        sentence that includes the wellness disclaimer.
        """
        if response_schema is not None:
            return self._fake_dict_for_schema(response_schema)

        h = _hash_inputs(system, user)
        # Use seeded random to get deterministic short sentence
        rng = random.Random(h)
        word_index = rng.randint(0, 4)
        words = [
            "Your habits show great potential.",
            "Consistency is the key to longevity.",
            "Small steps lead to lasting changes.",
            "Your sleep data suggests room for improvement.",
            "Movement is medicine for long-term health.",
        ]
        sentence = words[word_index]
        return f"{sentence} {_DISCLAIMER}"

    def generate_stream(
        self,
        *,
        system: str,
        user: str,
        model: str,
    ) -> AsyncIterator[str]:
        """Return an async iterator yielding the fixed token sequence ``_STREAM_TOKENS``."""
        return _token_stream()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return deterministic 768-d vectors in [-1, 1] keyed by text hash.

        Uses MD5 for cross-platform determinism (same as ``_hash_inputs``).
        """
        result: list[list[float]] = []
        for text in texts:
            h = int(hashlib.md5(text.encode()).hexdigest(), 16)
            rng = random.Random(h)
            vector = [rng.uniform(-1.0, 1.0) for _ in range(768)]
            result.append(vector)
        return result

    async def generate_vision(
        self,
        *,
        system: str,
        prompt: str,
        image_bytes: bytes,
        model: str,
        response_schema: type[BaseModel],
    ) -> dict:
        """Return a fixed ``MealAnalysis``-shaped dict."""
        return dict(_FAKE_VISION)

    @staticmethod
    def _fake_dict_for_schema(schema: type[BaseModel]) -> dict:
        """Build a default-value dict from a Pydantic schema's field defaults.

        This creates a model instance using only default values (no required
        fields must be set since the fake always uses field defaults), then
        dumps it to a plain dict.  If instantiation fails, falls back to an
        empty dict — tests should use schemas with complete defaults.
        """
        try:
            instance = schema()
            return instance.model_dump()
        except Exception:
            return {}


async def _token_stream() -> AsyncIterator[str]:
    """Async generator that yields the fixed token sequence."""
    for token in _STREAM_TOKENS:
        yield token


# ---------------------------------------------------------------------------
# GeminiProvider — real Vertex AI client
# ---------------------------------------------------------------------------


class GeminiProvider:
    """Production LLM provider backed by Gemini on Vertex AI.

    Uses ``from google import genai`` (the ``google-genai`` package).  Never
    use ``google-generativeai`` or ``vertexai.generative_models`` — both are
    deprecated or wrong packages for this stack.

    The client is constructed with ``vertexai=True`` so all calls are routed
    through Vertex AI and billed to the GCP project.  Data stays in the
    ``location`` region (``europe-west3`` by default for EU data residency).

    Args:
        project: GCP project ID, e.g. ``"my-longevity-project"``.
        location: GCP region, e.g. ``"europe-west3"``.
    """

    def __init__(self, project: str, location: str) -> None:
        self._client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )

    async def generate(
        self,
        *,
        system: str,
        user: str,
        model: str,
        response_schema: type[BaseModel] | None = None,
    ) -> str | dict:
        """Call Gemini to generate text or structured JSON.

        When ``response_schema`` is provided, sets ``response_mime_type`` to
        ``"application/json"`` and passes the schema as ``response_schema`` in
        ``GenerateContentConfig``.

        Args:
            system: System instruction text.
            user: User message text.
            model: Gemini model identifier.
            response_schema: Optional Pydantic schema for structured output.

        Returns:
            Plain text string or ``dict`` (when ``response_schema`` is set).
        """
        config_kwargs: dict = {
            "system_instruction": system,
        }
        if response_schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_schema

        config = genai.types.GenerateContentConfig(**config_kwargs)
        response = self._client.models.generate_content(
            model=model,
            contents=user,
            config=config,
        )
        if response_schema is not None:
            import json
            return json.loads(response.text)
        return response.text

    def generate_stream(
        self,
        *,
        system: str,
        user: str,
        model: str,
    ) -> AsyncIterator[str]:
        """Return an async iterator streaming text tokens from Gemini.

        Yields individual chunk texts from ``generate_content_stream``.

        Args:
            system: System instruction text.
            user: User message text.
            model: Gemini model identifier.

        Returns:
            Async iterator of text token chunks.
        """
        return _gemini_stream(self._client, system=system, user=user, model=model)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts using ``text-embedding-004`` on Vertex AI.

        Args:
            texts: Strings to embed.

        Returns:
            List of 768-d float vectors.
        """
        response = self._client.models.embed_content(
            model="text-embedding-004",
            contents=texts,
        )
        return [emb.values for emb in response.embeddings]

    async def generate_vision(
        self,
        *,
        system: str,
        prompt: str,
        image_bytes: bytes,
        model: str,
        response_schema: type[BaseModel],
    ) -> dict:
        """Analyse an image and return structured JSON via Gemini Vision.

        Passes the image as a ``Part`` alongside the text prompt.  Uses
        structured output (``response_mime_type="application/json"``).

        Args:
            system: System instruction text.
            prompt: Textual question / instruction about the image.
            image_bytes: Raw image bytes (JPEG or PNG).
            model: Gemini model identifier (must support vision).
            response_schema: Pydantic schema for the expected JSON output.

        Returns:
            ``dict`` conforming to ``response_schema``.
        """
        import json

        image_part = genai.types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/jpeg",
        )
        config = genai.types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=response_schema,
        )
        response = self._client.models.generate_content(
            model=model,
            contents=[prompt, image_part],
            config=config,
        )
        return json.loads(response.text)


async def _gemini_stream(
    client: genai.Client,
    *,
    system: str,
    user: str,
    model: str,
) -> AsyncIterator[str]:
    """Async generator that yields text chunks from a Gemini streaming call."""
    config = genai.types.GenerateContentConfig(system_instruction=system)
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=user,
        config=config,
    ):
        if chunk.text:
            yield chunk.text


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_llm_provider(settings: object) -> LLMProvider:
    """Return the LLM provider configured via application settings.

    Args:
        settings: A ``Settings`` instance (or compatible object) with
            ``llm_provider``, ``gcp_project``, and ``gcp_location`` fields.

    Returns:
        A ``FakeLLMProvider`` when ``settings.llm_provider == "fake"``, or a
        ``GeminiProvider`` when ``settings.llm_provider == "gemini"``.

    Raises:
        ValueError: For unrecognised ``llm_provider`` values.
    """
    provider: str = getattr(settings, "llm_provider", "fake")
    if provider == "fake":
        return FakeLLMProvider()
    if provider == "gemini":
        project: str = getattr(settings, "gcp_project", "") or ""
        location: str = getattr(settings, "gcp_location", "europe-west3")
        return GeminiProvider(project=project, location=location)
    raise ValueError(f"Unknown llm_provider: {provider!r}. Expected 'fake' or 'gemini'.")
