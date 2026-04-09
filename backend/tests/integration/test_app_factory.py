"""Integration tests for the main.py app factory (T16).

Covers:
- OpenAPI route listing (expected paths present)
- Health endpoint liveness (200, no auth)
- Request-ID header echoed on arbitrary request
- Request-ID preserved when supplied by caller
- App title and version from openapi() metadata
"""

from __future__ import annotations

import re
import uuid

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Fixtures — we build a fresh app per test module rather than relying on the
# session-scoped app_client, because the app factory tests care about the app
# object itself, not about a DB-backed session.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
async def client() -> AsyncClient:  # type: ignore[return]
    """Return an in-process AsyncClient wired to a freshly created app.

    Uses httpx ASGITransport so no real TCP socket is opened.
    The session dependency is NOT overridden here — we test the app in its
    'no DB' state; routes that need DB will return 500/422, but the factory
    tests only call /healthz and /openapi.json which need no DB session.
    """
    from httpx import AsyncClient
    from httpx._transports.asgi import ASGITransport

    from app.main import create_app

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_app_openapi_lists_expected_routes(client: AsyncClient) -> None:
    """OpenAPI spec must declare all required paths.

    The paths correspond to the mockup contract endpoints:
    - /healthz                                (health)
    - /patients/{patient_id}                  (patient profile)
    - /patients/{patient_id}/vitality         (vitality score)
    - /patients/{patient_id}/records          (EHR records list)
    - /patients/{patient_id}/insights         (wellness insights)
    - /patients/{patient_id}/appointments/    (appointments stub)
    - /patients/{patient_id}/gdpr/export      (GDPR Art. 15 export)
    """
    response = await client.get("/openapi.json")
    assert response.status_code == 200

    paths = set(response.json()["paths"].keys())

    expected = {
        "/healthz",
        "/patients/{patient_id}",
        "/patients/{patient_id}/vitality",
        "/patients/{patient_id}/records",
        "/patients/{patient_id}/insights",
        "/patients/{patient_id}/appointments/",
        "/patients/{patient_id}/gdpr/export",
    }
    missing = expected - paths
    assert not missing, f"OpenAPI spec is missing paths: {missing}"


@pytest.mark.asyncio
async def test_app_health_endpoint_returns_200(client: AsyncClient) -> None:
    """GET /healthz must return 200 without any authentication header."""
    response = await client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body.get("status") == "ok"


@pytest.mark.asyncio
async def test_request_id_header_is_echoed(client: AsyncClient) -> None:
    """A request without X-Request-ID must get a UUID echoed back in the response."""
    response = await client.get("/healthz")
    assert response.status_code == 200

    request_id = response.headers.get("x-request-id")
    assert request_id is not None, "X-Request-ID header missing from response"

    # Must be a valid UUID4 (any version accepted — we check UUID format)
    try:
        uuid.UUID(request_id)
    except ValueError:
        pytest.fail(f"X-Request-ID is not a valid UUID: {request_id!r}")


@pytest.mark.asyncio
async def test_request_id_header_preserved_when_supplied(client: AsyncClient) -> None:
    """When the caller supplies X-Request-ID, the response must echo the same value."""
    custom_id = "foo-bar-baz"
    response = await client.get("/healthz", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200

    echoed = response.headers.get("x-request-id")
    assert echoed == custom_id, (
        f"Expected X-Request-ID to be echoed as {custom_id!r}, got {echoed!r}"
    )


@pytest.mark.asyncio
async def test_app_title_and_version(client: AsyncClient) -> None:
    """OpenAPI metadata must carry the expected title and version strings."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200

    spec = response.json()
    info = spec.get("info", {})

    assert info.get("title") == "Longevity+ Backend", (
        f"Unexpected title: {info.get('title')!r}"
    )
    assert info.get("version") == "0.1.0", (
        f"Unexpected version: {info.get('version')!r}"
    )
