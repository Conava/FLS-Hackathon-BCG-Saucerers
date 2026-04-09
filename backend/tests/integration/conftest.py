"""
Integration test configuration.

The `compose` marker is defined here so pytest does not emit an "unknown mark"
warning when the test module is collected without the root pyproject.toml
marker registration (which lives in T1's pyproject.toml).
"""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "compose: marks tests that require a running docker-compose stack "
        "(skipped in CI by default — run with -m compose locally)",
    )
