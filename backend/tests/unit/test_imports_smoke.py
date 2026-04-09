"""Smoke tests: verify new Wave 1 dependencies are importable."""


def test_google_genai_importable() -> None:
    """Assert that the google-genai SDK (NOT google-generativeai) can be imported."""
    from google import genai  # noqa: F401


def test_sse_starlette_importable() -> None:
    """Assert that sse-starlette is importable."""
    import sse_starlette  # noqa: F401


def test_google_cloud_storage_importable() -> None:
    """Assert that google-cloud-storage is importable."""
    from google.cloud import storage  # noqa: F401
