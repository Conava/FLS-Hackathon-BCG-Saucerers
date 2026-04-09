"""Prompt loader — reads system prompt files from ``app/ai/prompts/``.

All prompt files follow the naming convention ``<name>.md`` and live under
the ``prompts/`` directory that is co-located with this module.  Reads are
cached via ``functools.lru_cache`` so the filesystem is only accessed once
per unique name over the lifetime of the process.

Usage::

    from app.ai.prompt_loader import load_prompt

    system_text = load_prompt("coach.system")

Raises:
    FileNotFoundError: if ``<name>.md`` does not exist under ``prompts/``.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_PROMPTS_DIR: Path = Path(__file__).parent / "prompts"


@lru_cache(maxsize=128)
def load_prompt(name: str) -> str:
    """Return the content of ``prompts/<name>.md``, cached after the first read.

    Args:
        name: Prompt name without the ``.md`` extension, e.g. ``"coach.system"``.

    Returns:
        The full text content of the prompt file.

    Raises:
        FileNotFoundError: with message ``"prompt not found: <name>"`` when the
            file does not exist.
    """
    path = _PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"prompt not found: {name}")
    return path.read_text(encoding="utf-8")
