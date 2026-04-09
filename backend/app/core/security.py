"""FastAPI dependency that enforces X-API-Key authentication.

Design notes:
- The configured ``API_KEY`` is read from :class:`~app.core.config.Settings`
  on every request, not at import time.  This makes the dep trivially
  testable via ``monkeypatch.setenv`` without module-level caching issues.
- Returns ``None`` on success (the route does not receive a key value).
- Raises :class:`fastapi.HTTPException` with status 401 on any mismatch.

PHI note: the API key is a shared secret — it contains no patient data and
is never logged.
"""
from fastapi import Header, HTTPException, status

from app.core.config import Settings


async def api_key_auth(x_api_key: str | None = Header(default=None)) -> None:
    """Validate the ``X-API-Key`` request header.

    Reads the expected key from ``Settings`` on each invocation so that
    environment changes (e.g. in tests) are picked up without restart.

    Args:
        x_api_key: Value from the ``X-API-Key`` HTTP header, or ``None`` if
            the header is absent.

    Raises:
        HTTPException: 401 Unauthorized when the header is absent, empty,
            or does not match the configured ``API_KEY``.
    """
    settings = Settings()
    expected = settings.api_key

    if not x_api_key or x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
