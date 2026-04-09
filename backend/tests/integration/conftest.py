"""
Integration test configuration.

The `compose` marker is defined here so pytest does not emit an "unknown mark"
warning when the test module is collected without the root pyproject.toml
marker registration (which lives in T1's pyproject.toml).
"""

import os

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "compose: marks tests that require a running docker-compose stack "
        "(skipped in CI by default — run with -m compose locally)",
    )


@pytest.fixture(scope="session", autouse=True)
def _force_test_env_vars() -> None:
    """Force-set env vars required by all integration router tests.

    Using force-set (not setdefault) so the test suite is not affected by
    whatever the caller shell has in its environment.  These are test-only
    values — no production secrets are involved.
    """
    os.environ["API_KEY"] = "test-key"
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://ignored")
