"""Integration tests for the main.py app factory (T16).

Covers:
- OpenAPI route listing (expected paths present)
- Health endpoint liveness (200, no auth)
- Request-ID header echoed on arbitrary request
- Request-ID preserved when supplied by caller
- App title and version from openapi() metadata
"""

from __future__ import annotations

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
        # Slice 1 — foundation routes
        "/healthz",
        "/v1/patients/{patient_id}",
        "/v1/patients/{patient_id}/vitality",
        "/v1/patients/{patient_id}/records",
        "/v1/patients/{patient_id}/insights",
        "/v1/patients/{patient_id}/appointments/",
        "/v1/patients/{patient_id}/gdpr/export",
        # Slice 2 — Wave 3 routers
        "/v1/patients/{patient_id}/records/qa",
        "/v1/patients/{patient_id}/coach/chat",
        "/v1/patients/{patient_id}/protocol/generate",
        "/v1/patients/{patient_id}/protocol",
        "/v1/patients/{patient_id}/protocol/complete-action",
        "/v1/patients/{patient_id}/survey",
        "/v1/patients/{patient_id}/survey/history",
        "/v1/patients/{patient_id}/daily-log",
        "/v1/patients/{patient_id}/meal-log",
        "/v1/patients/{patient_id}/insights/outlook-narrator",
        "/v1/patients/{patient_id}/insights/future-self",
        "/v1/patients/{patient_id}/outlook",
        "/v1/patients/{patient_id}/notifications/smart",
        "/v1/patients/{patient_id}/clinical-review",
        "/v1/patients/{patient_id}/referral",
        "/v1/patients/{patient_id}/messages",
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


@pytest.mark.asyncio
async def test_v1_prefix_migration_old_path_404_new_path_in_spec(
    client: AsyncClient,
) -> None:
    """Regression: old root paths must be gone (404); /v1 paths must exist in spec.

    Asserts that:
    - GET /patients/PT0001/profile (old, root-mounted path) returns 404.
    - /v1/patients/{patient_id} is present in the OpenAPI spec.

    This is the canonical regression guard for the T1 /v1 prefix migration.
    """
    # Old path must not exist — 404 (or 405 for wrong method, but 404 for path not found).
    old_path_resp = await client.get("/patients/PT0001/profile")
    assert old_path_resp.status_code == 404, (
        f"Old path /patients/PT0001/profile must return 404 after /v1 migration, "
        f"got {old_path_resp.status_code}"
    )

    # New /v1 path must be declared in the OpenAPI spec.
    openapi_resp = await client.get("/openapi.json")
    assert openapi_resp.status_code == 200
    paths = set(openapi_resp.json()["paths"].keys())
    assert "/v1/patients/{patient_id}" in paths, (
        f"/v1/patients/{{patient_id}} not found in OpenAPI paths: {paths}"
    )
