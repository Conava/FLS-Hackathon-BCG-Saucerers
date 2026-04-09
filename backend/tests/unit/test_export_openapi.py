"""Unit tests for the OpenAPI export CLI.

Covers:
- Output is valid JSON.
- ``openapi`` field starts with ``"3.1"``.
- ``info.version`` equals ``"1.0.0"`` (set in ``create_app``).
- ``info.title`` equals ``"Longevity+ API"``.
- The CLI can write to an arbitrary temp path without side-effects.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.cli.export_openapi import export


def test_export_writes_valid_json(tmp_path: Path) -> None:
    """The exported file must be parseable JSON."""
    dest = tmp_path / "openapi.json"
    export(dest)
    content = dest.read_text(encoding="utf-8")
    # Must not raise
    parsed = json.loads(content)
    assert isinstance(parsed, dict)


def test_export_openapi_version_31(tmp_path: Path) -> None:
    """The ``openapi`` field must advertise OpenAPI 3.1.x."""
    dest = tmp_path / "openapi.json"
    export(dest)
    schema = json.loads(dest.read_text(encoding="utf-8"))
    assert schema["openapi"].startswith("3.1"), (
        f"Expected openapi version to start with '3.1', got {schema['openapi']!r}"
    )


def test_export_info_version(tmp_path: Path) -> None:
    """``info.version`` must be ``'1.0.0'`` as set in ``create_app``."""
    dest = tmp_path / "openapi.json"
    export(dest)
    schema = json.loads(dest.read_text(encoding="utf-8"))
    assert schema["info"]["version"] == "1.0.0", (
        f"Expected info.version='1.0.0', got {schema['info']['version']!r}"
    )


def test_export_info_title(tmp_path: Path) -> None:
    """``info.title`` must be ``'Longevity+ API'``."""
    dest = tmp_path / "openapi.json"
    export(dest)
    schema = json.loads(dest.read_text(encoding="utf-8"))
    assert schema["info"]["title"] == "Longevity+ API"


def test_export_trailing_newline(tmp_path: Path) -> None:
    """Output must end with exactly one newline for clean git diffs."""
    dest = tmp_path / "openapi.json"
    export(dest)
    raw = dest.read_bytes()
    assert raw.endswith(b"\n"), "File must end with a trailing newline"
    assert not raw.endswith(b"\n\n"), "File must not end with double newline"


def test_export_deterministic(tmp_path: Path) -> None:
    """Two consecutive exports must produce byte-identical output."""
    dest_a = tmp_path / "a.json"
    dest_b = tmp_path / "b.json"
    export(dest_a)
    export(dest_b)
    assert dest_a.read_bytes() == dest_b.read_bytes(), (
        "export() must be deterministic (sort_keys=True)"
    )
