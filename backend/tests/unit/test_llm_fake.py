"""Unit tests for FakeLLMProvider and GeminiProvider construction.

All tests are purely local — no network calls, no GCP credentials needed.
GeminiProvider construction is verified by monkeypatching genai.Client.
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def collect_stream(aiter: AsyncIterator[str]) -> list[str]:
    """Drain an async iterator into a list."""
    results: list[str] = []
    async for chunk in aiter:
        results.append(chunk)
    return results


# ---------------------------------------------------------------------------
# FakeLLMProvider — determinism
# ---------------------------------------------------------------------------


class TestFakeLLMProviderDeterminism:
    """Same inputs always produce the same outputs from FakeLLMProvider."""

    async def test_generate_text_deterministic(self) -> None:
        """generate() with the same system+user returns the same string each time."""
        from app.ai.llm import FakeLLMProvider

        provider = FakeLLMProvider()
        result1 = await provider.generate(
            system="You are a health coach.",
            user="How should I sleep better?",
            model="gemini-2.5-flash",
        )
        result2 = await provider.generate(
            system="You are a health coach.",
            user="How should I sleep better?",
            model="gemini-2.5-flash",
        )
        assert result1 == result2

    async def test_generate_text_differs_for_different_inputs(self) -> None:
        """generate() with different user messages returns different strings."""
        from app.ai.llm import FakeLLMProvider

        provider = FakeLLMProvider()
        result_a = await provider.generate(
            system="You are a health coach.",
            user="Tell me about sleep.",
            model="gemini-2.5-flash",
        )
        result_b = await provider.generate(
            system="You are a health coach.",
            user="Tell me about nutrition.",
            model="gemini-2.5-flash",
        )
        assert result_a != result_b

    async def test_generate_with_schema_returns_dict(self) -> None:
        """generate() with response_schema returns a dict, not a string."""
        from app.ai.llm import FakeLLMProvider

        class MySchema(BaseModel):
            title: str = "default title"
            score: int = 0

        provider = FakeLLMProvider()
        result = await provider.generate(
            system="Generate a response.",
            user="Give me a protocol.",
            model="gemini-2.5-pro",
            response_schema=MySchema,
        )
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

    async def test_generate_schema_deterministic(self) -> None:
        """generate() with schema returns same dict for same inputs each time."""
        from app.ai.llm import FakeLLMProvider

        class MySchema(BaseModel):
            title: str = "default"
            value: float = 1.0

        provider = FakeLLMProvider()
        r1 = await provider.generate(
            system="sys", user="usr", model="gemini-2.5-pro", response_schema=MySchema
        )
        r2 = await provider.generate(
            system="sys", user="usr", model="gemini-2.5-pro", response_schema=MySchema
        )
        assert r1 == r2


# ---------------------------------------------------------------------------
# FakeLLMProvider — disclaimer
# ---------------------------------------------------------------------------


class TestFakeLLMProviderDisclaimer:
    """Text generate output contains the 'Not medical advice' disclaimer."""

    async def test_generate_text_contains_disclaimer(self) -> None:
        """Text response from generate() includes the medical advice disclaimer."""
        from app.ai.llm import FakeLLMProvider

        provider = FakeLLMProvider()
        result = await provider.generate(
            system="Health coach.",
            user="What should I eat?",
            model="gemini-2.5-flash",
        )
        assert isinstance(result, str)
        assert "not medical advice" in result.lower(), (
            f"Expected disclaimer in output, got: {result!r}"
        )


# ---------------------------------------------------------------------------
# FakeLLMProvider — streaming
# ---------------------------------------------------------------------------


class TestFakeLLMProviderStream:
    """generate_stream() yields a non-empty fixed token sequence."""

    async def test_stream_yields_tokens(self) -> None:
        """generate_stream yields at least one string token."""
        from app.ai.llm import FakeLLMProvider

        provider = FakeLLMProvider()
        tokens = await collect_stream(
            provider.generate_stream(
                system="Health coach.",
                user="Tell me something.",
                model="gemini-2.5-flash",
            )
        )
        assert len(tokens) > 0, "Expected at least one token from stream"

    async def test_stream_tokens_are_strings(self) -> None:
        """All yielded tokens are non-empty strings."""
        from app.ai.llm import FakeLLMProvider

        provider = FakeLLMProvider()
        tokens = await collect_stream(
            provider.generate_stream(
                system="Health coach.",
                user="Tell me something.",
                model="gemini-2.5-flash",
            )
        )
        for tok in tokens:
            assert isinstance(tok, str), f"Token is not a string: {tok!r}"
            assert len(tok) > 0, "Token is empty string"

    async def test_stream_deterministic(self) -> None:
        """Same inputs yield the same token sequence each time."""
        from app.ai.llm import FakeLLMProvider

        provider = FakeLLMProvider()
        tokens1 = await collect_stream(
            provider.generate_stream(system="sys", user="usr", model="gemini-2.5-flash")
        )
        tokens2 = await collect_stream(
            provider.generate_stream(system="sys", user="usr", model="gemini-2.5-flash")
        )
        assert tokens1 == tokens2


# ---------------------------------------------------------------------------
# FakeLLMProvider — embeddings
# ---------------------------------------------------------------------------


class TestFakeLLMProviderEmbed:
    """embed() returns deterministic 768-dimensional vectors."""

    async def test_embed_returns_correct_dimensions(self) -> None:
        """embed() returns a list of 768-float vectors, one per input text."""
        from app.ai.llm import FakeLLMProvider

        provider = FakeLLMProvider()
        texts = ["Hello world", "How are you"]
        result = await provider.embed(texts)
        assert len(result) == 2, f"Expected 2 vectors, got {len(result)}"
        for vec in result:
            assert len(vec) == 768, f"Expected 768 dimensions, got {len(vec)}"

    async def test_embed_single_text_768d(self) -> None:
        """embed() on a single text returns a list with one 768-float vector."""
        from app.ai.llm import FakeLLMProvider

        provider = FakeLLMProvider()
        result = await provider.embed(["Longevity science is fascinating."])
        assert len(result) == 1
        assert len(result[0]) == 768

    async def test_embed_deterministic(self) -> None:
        """Same text always produces the same embedding vector."""
        from app.ai.llm import FakeLLMProvider

        provider = FakeLLMProvider()
        text = "Consistent embeddings are important."
        r1 = await provider.embed([text])
        r2 = await provider.embed([text])
        assert r1 == r2

    async def test_embed_different_texts_differ(self) -> None:
        """Different texts produce different embedding vectors."""
        from app.ai.llm import FakeLLMProvider

        provider = FakeLLMProvider()
        r1 = await provider.embed(["apple"])
        r2 = await provider.embed(["orange"])
        assert r1 != r2

    async def test_embed_values_in_range(self) -> None:
        """All embedding values are floats in [-1, 1]."""
        from app.ai.llm import FakeLLMProvider

        provider = FakeLLMProvider()
        result = await provider.embed(["test text for range check"])
        for val in result[0]:
            assert isinstance(val, float), f"Expected float, got {type(val)}"
            assert -1.0 <= val <= 1.0, f"Value {val} is out of range [-1, 1]"


# ---------------------------------------------------------------------------
# FakeLLMProvider — vision
# ---------------------------------------------------------------------------


class TestFakeLLMProviderVision:
    """generate_vision() returns a dict conforming to MealAnalysis shape."""

    async def test_generate_vision_returns_dict(self) -> None:
        """generate_vision returns a dict (not a string)."""
        from app.ai.llm import FakeLLMProvider

        class MealAnalysis(BaseModel):
            classification: str = "grilled chicken"
            macros: dict = {}
            longevity_swap: str = ""
            swap_rationale: str = ""

        provider = FakeLLMProvider()
        result = await provider.generate_vision(
            system="Analyze this meal photo.",
            prompt="What macros does this meal have?",
            image_bytes=b"\x89PNG\r\n",
            model="gemini-2.5-flash",
            response_schema=MealAnalysis,
        )
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

    async def test_generate_vision_has_required_keys(self) -> None:
        """generate_vision dict contains classification and macros keys."""
        from app.ai.llm import FakeLLMProvider

        class MealAnalysis(BaseModel):
            classification: str = "grilled chicken"
            macros: dict = {}
            longevity_swap: str = ""
            swap_rationale: str = ""

        provider = FakeLLMProvider()
        result = await provider.generate_vision(
            system="Analyze this meal.",
            prompt="Identify macros.",
            image_bytes=b"fake-image-data",
            model="gemini-2.5-flash",
            response_schema=MealAnalysis,
        )
        assert "classification" in result
        assert "macros" in result


# ---------------------------------------------------------------------------
# Factory — get_llm_provider
# ---------------------------------------------------------------------------


class TestGetLlmProviderFactory:
    """get_llm_provider() returns the right class based on settings."""

    def test_factory_returns_fake_provider_by_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_llm_provider returns FakeLLMProvider when llm_provider='fake'."""
        from app.ai.llm import FakeLLMProvider, get_llm_provider
        from app.core.config import Settings

        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
        monkeypatch.setenv("API_KEY", "key")
        monkeypatch.setenv("LLM_PROVIDER", "fake")
        settings = Settings()
        provider = get_llm_provider(settings)
        assert isinstance(provider, FakeLLMProvider)

    def test_factory_returns_gemini_provider_when_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_llm_provider returns GeminiProvider when llm_provider='gemini'."""
        from app.ai.llm import GeminiProvider, get_llm_provider
        from app.core.config import Settings

        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
        monkeypatch.setenv("API_KEY", "key")
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("GCP_PROJECT", "my-project")
        monkeypatch.setenv("GCP_LOCATION", "europe-west3")

        # Patch genai.Client so no real network call is made
        with patch("app.ai.llm.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()
            settings = Settings()
            provider = get_llm_provider(settings)

        assert isinstance(provider, GeminiProvider)


# ---------------------------------------------------------------------------
# GeminiProvider — construction (monkeypatched, no network)
# ---------------------------------------------------------------------------


class TestGeminiProviderConstruction:
    """GeminiProvider uses vertexai=True and the settings values when constructing."""

    def test_gemini_provider_uses_vertexai_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """GeminiProvider constructs genai.Client with vertexai=True."""
        with patch("app.ai.llm.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            from app.ai.llm import GeminiProvider
            GeminiProvider(project="test-project", location="europe-west3")

            mock_genai.Client.assert_called_once()
            call_kwargs = mock_genai.Client.call_args.kwargs
            assert call_kwargs.get("vertexai") is True

    def test_gemini_provider_passes_project(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """GeminiProvider passes the project argument to genai.Client."""
        with patch("app.ai.llm.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()

            from app.ai.llm import GeminiProvider
            GeminiProvider(project="my-gcp-project", location="europe-west3")

            call_kwargs = mock_genai.Client.call_args.kwargs
            assert call_kwargs.get("project") == "my-gcp-project"

    def test_gemini_provider_passes_location(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """GeminiProvider passes the location argument to genai.Client."""
        with patch("app.ai.llm.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()

            from app.ai.llm import GeminiProvider
            GeminiProvider(project="proj", location="europe-west3")

            call_kwargs = mock_genai.Client.call_args.kwargs
            assert call_kwargs.get("location") == "europe-west3"
