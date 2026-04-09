"""Unit tests for app.ai.prompt_loader — load_prompt() hit/miss/cache behaviour."""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


class TestLoadPromptHit:
    """Prompt loader returns content when the file exists."""

    def test_returns_string_for_existing_prompt(self) -> None:
        """load_prompt('coach.system') returns a non-empty string."""
        from app.ai.prompt_loader import load_prompt

        result = load_prompt("coach.system")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_correct_content(self) -> None:
        """load_prompt returns the actual file content (not empty or wrong prompt)."""
        from app.ai.prompt_loader import load_prompt

        result = load_prompt("records-qa.system")
        # records-qa prompt should mention citations/records
        assert "record" in result.lower() or "citation" in result.lower() or "records" in result.lower()

    def test_all_prompts_are_loadable(self) -> None:
        """All seven required prompt files can be loaded."""
        from app.ai.prompt_loader import load_prompt

        prompt_names = [
            "coach.system",
            "records-qa.system",
            "protocol-generator.system",
            "meal-vision.system",
            "outlook-narrator.system",
            "future-self.system",
            "notifications.system",
        ]
        for name in prompt_names:
            result = load_prompt(name)
            assert isinstance(result, str), f"Prompt '{name}' did not return a string"
            assert len(result) > 0, f"Prompt '{name}' returned empty content"


class TestLoadPromptMiss:
    """Prompt loader raises FileNotFoundError for unknown prompt names."""

    def test_missing_prompt_raises_file_not_found(self) -> None:
        """load_prompt raises FileNotFoundError when the prompt file does not exist."""
        from app.ai.prompt_loader import load_prompt

        with pytest.raises(FileNotFoundError, match="prompt not found: nonexistent-prompt"):
            load_prompt("nonexistent-prompt")

    def test_error_message_contains_prompt_name(self) -> None:
        """The FileNotFoundError message includes the exact prompt name requested."""
        from app.ai.prompt_loader import load_prompt

        prompt_name = "i-do-not-exist.system"
        with pytest.raises(FileNotFoundError, match=prompt_name):
            load_prompt(prompt_name)


class TestLoadPromptCache:
    """Prompt loader caches file reads; the second call does not re-read from disk."""

    def test_second_call_uses_cache(self) -> None:
        """load_prompt is idempotent and returns the same object on repeated calls."""
        from app.ai.prompt_loader import load_prompt

        first = load_prompt("coach.system")
        second = load_prompt("coach.system")
        # Same string value
        assert first == second

    def test_cache_avoids_disk_reads(self, tmp_path: Path) -> None:
        """After the first call, load_prompt does not re-open the file on disk.

        We verify this by reimporting a fresh module instance (bypassing lru_cache),
        calling it once to prime the cache, then monkeypatching Path.read_text and
        confirming the second call succeeds without touching the filesystem.
        """
        # Reimport a fresh copy of the module to get a clean cache
        if "app.ai.prompt_loader" in sys.modules:
            del sys.modules["app.ai.prompt_loader"]

        import app.ai.prompt_loader as pm
        # Prime the cache
        first = pm.load_prompt("coach.system")

        read_count = 0
        original_read_text = Path.read_text

        def counting_read_text(self: Path, **kwargs: object) -> str:
            nonlocal read_count
            read_count += 1
            return original_read_text(self, **kwargs)  # type: ignore[arg-type]

        with patch.object(Path, "read_text", counting_read_text):
            second = pm.load_prompt("coach.system")

        assert second == first
        assert read_count == 0, "Expected no disk reads on second call; cache should be used"
