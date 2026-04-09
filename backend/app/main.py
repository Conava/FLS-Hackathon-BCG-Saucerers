"""FastAPI application factory for the Longevity+ backend.

This module is the composition root: it wires together config, structured
logging, request-id middleware, and all routers into a single runnable app.

Uvicorn entry-point::

    uvicorn app.main:app --host 0.0.0.0 --port 8080

Design decisions:

* ``create_app()`` is a factory function so that tests (and the conftest
  ``app_client`` fixture) can construct isolated app instances with
  dependency-override hooks applied before any request is processed.
* The module-level ``app = create_app()`` binding exists solely so uvicorn
  can resolve ``app.main:app`` without calling the factory itself.
* No database connection is opened at startup.  The engine is constructed
  lazily on first request by ``app.db.session.get_engine``; this means
  ``uvicorn`` boots even when ``DATABASE_URL`` is not set (useful in CI
  steps that only run linting or typing checks).
* PHI policy: the startup log emits only ``app_env`` (an enum-like label),
  never any patient data, connection strings, or API keys.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestIdMiddleware
from app.routers import appointments, gdpr, health, patients


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """ASGI lifespan handler — runs at startup and shutdown.

    Startup:
        1. Configure the root logger with JSON formatting and request-id filter.
        2. Emit a structured startup log (no PHI — only ``app_env``).

    Shutdown:
        1. Emit a structured shutdown log.

    The DB engine is NOT initialised here; ``get_engine()`` is lazy and
    opens its pool on first checkout (``pool_pre_ping=True``).

    Args:
        app: The ``FastAPI`` application instance (injected by Starlette's
             lifespan protocol).
    """
    # Read settings once — fine because Settings is read-only at this point.
    settings = Settings()
    configure_logging(log_level=settings.log_level)
    log = get_logger(__name__)
    log.info("app_starting", extra={"app_env": settings.app_env})

    yield

    log.info("app_stopping")


def create_app() -> FastAPI:
    """Construct and return a fully configured ``FastAPI`` application.

    Steps:
    1. Instantiate ``FastAPI`` with metadata (title, description, version) and
       the async ``lifespan`` handler.
    2. Register ``RequestIdMiddleware`` so every request gets an
       ``X-Request-ID`` header in both directions.
    3. Include all routers in registration order:
       - ``health``       → ``GET /healthz`` (unauthenticated liveness probe,
                             no ``/v1`` prefix — kept at root for probes)
       - ``patients``     → ``/v1/patients/{patient_id}/…`` (profile, vitality,
                             records, wearable, insights)
       - ``appointments`` → ``/v1/patients/{patient_id}/appointments/``
       - ``gdpr``         → ``/v1/patients/{patient_id}/gdpr/…``

    Returns:
        A ``FastAPI`` instance ready for use with uvicorn or an ASGI test
        transport (e.g. ``httpx.ASGITransport``).
    """
    app = FastAPI(
        title="Longevity+ Backend",
        description=(
            "Clinical-grade longevity MVP backend — wellness signals, not medical advice."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # Middleware is registered before routers so it wraps every incoming request.
    app.add_middleware(RequestIdMiddleware)

    # Routers are included in a stable order that matches the OpenAPI tag grouping.
    # health stays at root (unauthenticated liveness probe — no /v1 prefix).
    # All Slice 1 patient-domain routers are mounted under /v1 per the API contract.
    app.include_router(health.router)
    app.include_router(patients.router, prefix="/v1")
    app.include_router(appointments.router, prefix="/v1")
    app.include_router(gdpr.router, prefix="/v1")

    return app


# Module-level binding required by uvicorn:  uvicorn app.main:app
app = create_app()
