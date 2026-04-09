"""CLI to export the FastAPI OpenAPI schema to a JSON file.

Usage::

    python -m app.cli.export_openapi
    python -m app.cli.export_openapi /custom/path/openapi.json

The output is deterministic: keys are sorted, indented with two spaces, and a
single trailing newline is appended.  This makes ``git diff`` noise-free and
allows CI to detect schema drift by diffing the committed file against a freshly
generated one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Default output path is relative to the backend package root (two levels up
# from this file: app/cli/export_openapi.py → app/ → backend/).
_DEFAULT_OUTPUT = Path(__file__).parent.parent.parent / "openapi.json"


def export(output_path: Path | None = None) -> Path:
    """Generate the OpenAPI schema and write it to *output_path*.

    Args:
        output_path: Destination file path.  Defaults to
            ``backend/openapi.json``.

    Returns:
        The resolved path of the written file.
    """
    # Import here so the module is importable without a running app (e.g. in
    # unit tests that only import the function).
    from app.main import create_app  # noqa: PLC0415 — intentional lazy import

    resolved = (output_path or _DEFAULT_OUTPUT).resolve()

    application = create_app()
    schema = application.openapi()

    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return resolved


def main() -> None:
    """Entry-point for ``python -m app.cli.export_openapi [path]``."""
    output: Path | None = None
    if len(sys.argv) > 1:
        output = Path(sys.argv[1])

    written = export(output)
    print(f"OpenAPI schema written to {written}")  # noqa: T201


if __name__ == "__main__":
    main()
