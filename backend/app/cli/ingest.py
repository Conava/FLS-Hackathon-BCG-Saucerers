"""CLI entry-point: seed the database from a registered DataSource adapter.

Usage
-----
::

    python -m app.cli.ingest --source=csv [--data-dir=./data]

Options
-------
--source    Required. Name of the registered adapter (e.g. ``csv``).
--data-dir  Optional. Path to the data directory for adapters that need one.
            Defaults to ``./data`` relative to the current working directory.

Exit codes
----------
0   Ingest completed successfully.
1   Any error (adapter not found, DB error, etc.). Error message is printed
    to stderr; no PHI is included in the output.

PHI policy
----------
The CLI prints the ``IngestReport`` to stdout (patient count, record count,
duration) — no patient names or other PHI.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the ingest CLI.

    Returns
    -------
    argparse.ArgumentParser
        Configured parser with ``--source`` and ``--data-dir`` arguments.
    """
    parser = argparse.ArgumentParser(
        prog="python -m app.cli.ingest",
        description="Seed the Longevity+ database from a registered DataSource adapter.",
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Name of the registered adapter (e.g. 'csv').",
    )
    parser.add_argument(
        "--data-dir",
        default="./data",
        help="Path to the data directory (default: ./data).",
    )
    return parser


async def _run(source: str, data_dir: Path) -> None:
    """Async ingest runner.

    Creates the database schema (CREATE TABLE IF NOT EXISTS), opens an
    ``AsyncSession``, and runs ``UnifiedProfileService.ingest()``.

    Parameters
    ----------
    source:
        Registered adapter name (e.g. ``"csv"``).
    data_dir:
        Path forwarded to the adapter constructor.

    Raises
    ------
    Exception
        Any error propagates to the caller which converts it to a non-zero exit.
    """
    # Late imports so the module can be parsed without a live DB connection.
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    import app.adapters.csv_source  # noqa: F401 — side-effect: @register("csv") fires
    import app.models  # noqa: F401 — register SQLModel table metadata
    from app.ai.llm import get_llm_provider
    from app.core.config import get_settings
    from app.db.base import create_all
    from app.db.session import get_engine
    from app.services.unified_profile import UnifiedProfileService

    settings = get_settings()
    engine = get_engine()

    # Ensure schema exists (idempotent — CREATE TABLE IF NOT EXISTS)
    await create_all(engine)

    # Obtain LLM provider from settings so embeddings are populated during ingest.
    # With LLM_PROVIDER=fake (default) this uses FakeLLMProvider (no network calls).
    # With LLM_PROVIDER=gemini this uses the real Gemini embedding model.
    llm_provider = get_llm_provider(settings)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        svc = UnifiedProfileService(session, llm_provider=llm_provider)
        report = await svc.ingest(source, data_dir=data_dir)

    await engine.dispose()
    print(report)  # noqa: T201 — intentional CLI output


def main() -> None:
    """Parse arguments and run the async ingest, exiting non-zero on error.

    This is the synchronous entry-point called by ``python -m app.cli.ingest``.
    """
    parser = _build_parser()
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()

    try:
        asyncio.run(_run(source=args.source, data_dir=data_dir))
    except KeyError as exc:
        # Unknown adapter name — user-facing message, no PHI
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        # DB error, IO error, etc. — message only, no PHI
        print(f"Ingest failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
