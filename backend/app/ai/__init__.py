"""AI subsystem — LLM providers, prompt loader, and prompt files.

Public surface:
- ``LLMProvider`` — structural Protocol (runtime-checkable)
- ``FakeLLMProvider`` — deterministic in-process stub used by tests + dev
- ``GeminiProvider`` — real Gemini 2.5 via Vertex AI (``google-genai`` SDK)
- ``get_llm_provider(settings)`` — factory wired to application config
- ``load_prompt(name)`` — lru-cached file loader for ``prompts/*.md`` files
"""

from app.ai.llm import FakeLLMProvider, GeminiProvider, LLMProvider, get_llm_provider
from app.ai.prompt_loader import load_prompt

__all__ = [
    "FakeLLMProvider",
    "GeminiProvider",
    "LLMProvider",
    "get_llm_provider",
    "load_prompt",
]
