"""Smoke test: verifies the app package is importable."""


def test_package_importable() -> None:
    """Assert that the top-level app package can be imported without errors."""
    import app  # noqa: F401
