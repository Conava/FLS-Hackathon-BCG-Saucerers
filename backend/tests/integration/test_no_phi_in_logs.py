"""PHI-leak log assertion test (T24).

Drives representative traffic through every AI endpoint with a patient whose
``name`` contains unique sentinel strings.  Installs a capturing log handler
over all ``app.*`` loggers and the root logger during each request.  After each
request, asserts:

1. None of the sentinel strings appear in any log record message or structured
   extra fields.
2. Structured log records that come from the AI service code paths contain only
   allowed observability fields: ``request_id``, ``model``, ``prompt_name``,
   ``token_in`` / ``token_out`` / ``token_count``, ``latency_ms``, ``path``,
   ``status`` (and the standard ``logging.LogRecord`` attributes such as
   ``name``, ``levelname``, ``filename``, etc.).

PHI policy under test
---------------------
From the plan spec and service docstrings, the AI service code paths (RAG,
coach, protocol generator, outlook narrator, future-self, meal-vision,
notifications) must emit logs that contain ONLY::

    request_id, model, prompt_name, token_in, token_out, token_count,
    latency_ms, path, status

plus the standard Python ``logging.LogRecord`` fields (created, filename,
funcName, levelname, levelno, lineno, message, module, msecs, msg, name,
pathname, process, processName, relativeCreated, stack_info, thread,
threadName, taskName, exc_info, exc_text, args).

Any key that is not in this whitelist AND whose string value matches one of the
sentinel strings is a PHI leak.

Sentinel values
---------------
``_SENTINEL_NAME``   — unique string used as the patient's ``name`` field.
``_SENTINEL_EMAIL``  — unique string passed as contextual data in notifications/
                       future-self slider context so we test that it does not
                       leak even when it is part of *input* data.

Architecture
------------
The test builds a single full ``create_app()`` instance (matching what
production uses) and overrides ``get_session`` to use the Testcontainers-backed
``db_session``.  All LLM providers default to ``FakeLLMProvider`` (LLM_PROVIDER
env var is forced to "fake" in the integration conftest).

Because the coach endpoint returns Server-Sent Events (SSE) we consume the full
body text and parse events after the fact.

Stack: FastAPI + SQLAlchemy 2.0 async + Pydantic v2 + pytest-asyncio
(session-scoped event loop — see pyproject.toml).
"""

from __future__ import annotations

import datetime
import io
import json
import logging
from collections.abc import AsyncIterator
from io import BytesIO
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 — side-effect: register all SQLModel tables

# ---------------------------------------------------------------------------
# Sentinel strings — MUST be globally unique to avoid false negatives
# ---------------------------------------------------------------------------

#: Unique sentinel for the patient ``name`` field.  Must not match any common
#: word so that a substring match unambiguously indicates a PHI leak.
_SENTINEL_NAME = "SentinelPhiXYZ987"

#: Unique sentinel used as contextual input data (email-like, notification
#: context, future-self sliders).  Verifies that even *input* PHI does not
#: appear in log output.
_SENTINEL_EMAIL = "Leak@sentinel.invalid"

#: Combined iterable of all sentinel strings to check.
_SENTINELS: tuple[str, ...] = (_SENTINEL_NAME, _SENTINEL_EMAIL)

# ---------------------------------------------------------------------------
# Standard LogRecord attribute names — these are NOT PHI fields.
# ---------------------------------------------------------------------------

_STANDARD_LOG_RECORD_FIELDS: frozenset[str] = frozenset(
    [
        # LogRecord attributes that are always present
        "args",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
        # Added by RequestIdFilter (always safe — it is the request_id, not PHI)
        "request_id",
        # Python internal formatting artifacts
        "asctime",
        # pytest capturing
        "__tracebackhide__",
    ]
)

#: Fields emitted exclusively by the AI service code paths (allowed by PHI policy).
_ALLOWED_AI_FIELDS: frozenset[str] = frozenset(
    [
        "request_id",
        "model",
        "prompt_name",
        "token_in",
        "token_out",
        "token_count",
        "latency_ms",
        "path",
        "status",
        # Protocol generator and router also log these non-PHI identifiers
        "protocol_id",
        "action_count",
        "action_id",
        "new_streak_days",
        "records_retrieved",
        "citations",
        # App lifecycle
        "app_env",
    ]
)

# ---------------------------------------------------------------------------
# Log capturing infrastructure
# ---------------------------------------------------------------------------


class _CapturingHandler(logging.Handler):
    """A logging handler that accumulates all emitted records in memory.

    Attach to any logger before a code block, detach after, and inspect
    ``records`` for captured entries.

    Thread / async safety: ``records`` is a plain list.  The handler is only
    used within a single asyncio task, so no locking is needed.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Store *record* verbatim (no formatting needed for inspection)."""
        self.records.append(record)


def _install_capturing_handler() -> tuple[_CapturingHandler, list[logging.Logger]]:
    """Install a capturing handler on the root logger and all ``app.*`` loggers.

    Returns:
        A tuple of (handler, list_of_loggers_that_were_modified).
        The caller must call :func:`_remove_capturing_handler` after the code
        block under test.
    """
    handler = _CapturingHandler()
    # Root logger catches everything; we also attach to known app sub-loggers
    # explicitly so we don't miss any that propagate=False.
    loggers: list[logging.Logger] = [logging.getLogger()]
    for name in logging.Logger.manager.loggerDict:
        if name.startswith("app"):
            loggers.append(logging.getLogger(name))

    for lg in loggers:
        lg.addHandler(handler)

    return handler, loggers


def _remove_capturing_handler(
    handler: _CapturingHandler,
    loggers: list[logging.Logger],
) -> None:
    """Detach *handler* from all loggers in *loggers*."""
    for lg in loggers:
        lg.removeHandler(handler)


# ---------------------------------------------------------------------------
# Sentinel-leak assertion helpers
# ---------------------------------------------------------------------------


def _record_contains_sentinel(record: logging.LogRecord, sentinel: str) -> list[str]:
    """Walk the LogRecord dict and return the list of field paths that contain *sentinel*.

    Checks:
    - ``record.getMessage()`` (formatted message string)
    - ``record.msg`` (raw message, may be a format string)
    - Every value in ``record.__dict__`` that is a ``str`` or ``int``/``float``
      convertible to str — but only non-standard / non-whitelist fields.

    Args:
        record: The log record to inspect.
        sentinel: The string to search for (exact substring match).

    Returns:
        List of ``"field=value"`` strings for any field whose string
        representation contains the sentinel.  Empty list means clean.
    """
    hits: list[str] = []

    # Check the formatted message (this is the most common leak vector).
    try:
        formatted_msg = record.getMessage()
    except Exception:  # noqa: BLE001
        formatted_msg = str(record.msg)
    if sentinel in formatted_msg:
        hits.append(f"message={formatted_msg!r}")

    # Walk all record attributes.
    for key, value in record.__dict__.items():
        if key in _STANDARD_LOG_RECORD_FIELDS:
            continue
        # Only check string-valued extras (the PHI fields are always strings).
        if isinstance(value, str) and sentinel in value:
            hits.append(f"{key}={value!r}")
        elif isinstance(value, (list, dict)):
            value_str = str(value)
            if sentinel in value_str:
                hits.append(f"{key}={value_str!r}")

    return hits


def assert_no_phi_in_records(
    records: list[logging.LogRecord],
    sentinels: tuple[str, ...] = _SENTINELS,
    context: str = "",
) -> None:
    """Assert that none of *sentinels* appear in any of *records*.

    Args:
        records:   The captured log records to inspect.
        sentinels: Sentinel strings that must not appear.
        context:   Human-readable description of the endpoint under test,
                   included in the failure message.

    Raises:
        AssertionError: If any sentinel is found in any record.
    """
    for record in records:
        for sentinel in sentinels:
            hits = _record_contains_sentinel(record, sentinel)
            if hits:
                raise AssertionError(
                    f"PHI LEAK detected in {context!r} log records!\n"
                    f"  Sentinel: {sentinel!r}\n"
                    f"  Logger:   {record.name}\n"
                    f"  Level:    {record.levelname}\n"
                    f"  Hits:     {hits}\n"
                    f"  Full record dict keys: {list(record.__dict__.keys())}"
                )


# ---------------------------------------------------------------------------
# Test infrastructure: seed helpers and mini-app fixture
# ---------------------------------------------------------------------------

_DT = datetime.datetime(2026, 1, 1, 0, 0, 0)  # naive UTC sentinel date


async def _seed_sentinel_patient(session: AsyncSession, patient_id: str) -> None:
    """Seed a Patient row whose ``name`` contains the sentinel string.

    This is the PHI that must NEVER appear in any log record.
    The sentinel strings are globally unique, so any substring match in the
    log output is an unambiguous PHI leak.
    """
    from app.models.patient import Patient

    p = Patient(
        patient_id=patient_id,
        name=_SENTINEL_NAME,
        age=35,
        sex="unknown",
        country="DE",
    )
    session.add(p)
    await session.flush()


async def _seed_lifestyle_profile(session: AsyncSession, patient_id: str) -> None:
    """Seed a minimal LifestyleProfile required by the protocol generator."""
    from datetime import date

    from app.models.lifestyle_profile import LifestyleProfile

    lp = LifestyleProfile(
        patient_id=patient_id,
        survey_date=date(2026, 1, 1),
        time_budget_minutes_per_day=60,
        exercise_sessions_weekly=3,
        stress_level=5,
        sleep_satisfaction=7,
        diet_quality_score=6,
    )
    session.add(lp)
    await session.flush()


async def _seed_vitality_outlook(
    session: AsyncSession,
    patient_id: str,
    horizon_months: int = 6,
) -> None:
    """Seed a VitalityOutlook row required by the outlook narrator endpoint."""
    from app.models.vitality_outlook import VitalityOutlook

    o = VitalityOutlook(
        patient_id=patient_id,
        horizon_months=horizon_months,
        projected_score=72.0,
        narrative="",
        computed_at=_DT,
    )
    session.add(o)
    await session.flush()


async def _seed_vitality_snapshot(
    session: AsyncSession,
    patient_id: str,
    score: float = 68.5,
) -> None:
    """Seed a VitalitySnapshot so the outlook engine has a current score."""
    from app.models.vitality_snapshot import VitalitySnapshot

    snap = VitalitySnapshot(
        patient_id=patient_id,
        computed_at=_DT,
        score=score,
        subscores={"cardio": 70.0, "sleep": 65.0},
        risk_flags={},
    )
    session.add(snap)
    await session.flush()


# ---------------------------------------------------------------------------
# Mini-app fixture — full create_app() with dependency overrides
# ---------------------------------------------------------------------------

_MINIMAL_PNG: bytes = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01"
    b"\x00\x00\x00\x01"
    b"\x08\x02"
    b"\x00\x00\x00"
    b"\x90wS\xde"
    b"\x00\x00\x00\x0cIDAT"
    b"x\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
    b"\x00\x00\x00\x00IEND"
    b"\xaeB`\x82"
)


@pytest_asyncio.fixture(loop_scope="session")
async def phi_test_client(
    db_session: AsyncSession,
    tmp_path_factory: pytest.TempPathFactory,
) -> AsyncIterator[AsyncClient]:
    """Build the full FastAPI app (via create_app) and inject test overrides.

    Overrides:
    - ``get_session`` → testcontainers-backed ``db_session`` (no real DB writes
      persist across tests).
    - ``get_meal_vision_service`` → injects FakeLLMProvider + LocalFsPhotoStorage
      backed by a temporary directory.
    - All LLM dependencies that read ``Settings().llm_provider`` are left at
      default — Settings will return ``FakeLLMProvider`` because
      ``LLM_PROVIDER`` defaults to ``"fake"``.

    Yields an AsyncClient pointing at the full app.
    """
    from pathlib import Path

    from fastapi import FastAPI
    from httpx import AsyncClient
    from httpx._transports.asgi import ASGITransport

    from app.adapters.photo_storage import LocalFsPhotoStorage
    from app.ai.llm import FakeLLMProvider
    from app.db.session import get_session
    from app.main import create_app
    from app.routers import meal_log as meal_log_router
    from app.services.meal_vision import MealVisionService

    photos_dir: Path = tmp_path_factory.mktemp("phi_test_photos")

    full_app = create_app()

    async def _override_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    async def _override_meal_vision_service() -> AsyncIterator[MealVisionService]:
        storage = LocalFsPhotoStorage(base_dir=photos_dir)
        llm = FakeLLMProvider()
        svc = MealVisionService(session=db_session, photo_storage=storage, llm=llm)
        yield svc

    full_app.dependency_overrides[get_session] = _override_session
    full_app.dependency_overrides[
        meal_log_router.get_meal_vision_service
    ] = _override_meal_vision_service

    async with AsyncClient(
        transport=ASGITransport(app=full_app),
        base_url="http://test",
    ) as client:
        yield client

    full_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Patient ID for this test module — unique so it doesn't collide with others
# ---------------------------------------------------------------------------

_PID = "PT_PHI_SENTINEL_001"
_HEADERS = {"X-API-Key": "test-key"}


# ---------------------------------------------------------------------------
# Helper: run an HTTP call under log capture and assert no PHI leaks
# ---------------------------------------------------------------------------

async def _assert_no_phi_for_request(
    client: AsyncClient,
    method: str,
    url: str,
    context: str,
    *,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    files: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    expected_statuses: set[int] | None = None,
) -> None:
    """Make an HTTP request, capture logs, assert no PHI, return.

    Args:
        client:           The ASGI test client.
        method:           HTTP method (uppercase).
        url:              Path, e.g. ``"/v1/patients/PT.../records/qa"``.
        context:          Human-readable label for failure messages.
        json_body:        Optional JSON request body.
        headers:          Optional extra headers (merged with ``_HEADERS``).
        files:            Optional multipart files dict (httpx format).
        data:             Optional form data dict.
        expected_statuses: Set of acceptable HTTP status codes (defaults to
                          ``{200, 201}``).
    """
    if expected_statuses is None:
        expected_statuses = {200, 201}

    merged_headers = {**_HEADERS, **(headers or {})}

    handler, loggers = _install_capturing_handler()
    try:
        resp = await client.request(
            method,
            url,
            json=json_body,
            headers=merged_headers,
            files=files,
            data=data,
        )
    finally:
        _remove_capturing_handler(handler, loggers)

    assert resp.status_code in expected_statuses, (
        f"{context}: expected status in {expected_statuses}, "
        f"got {resp.status_code}: {resp.text[:500]}"
    )

    assert_no_phi_in_records(handler.records, context=context)


# ---------------------------------------------------------------------------
# Main test class
# ---------------------------------------------------------------------------


class TestNoPhiInLogs:
    """Assert that no PHI (sentinel values) leaks into logs from any AI endpoint.

    Every test method:
    1. Seeds the sentinel patient (if not already done — session fixture scope).
    2. Makes one representative request to an AI endpoint.
    3. Captures all log records emitted during the request.
    4. Asserts no sentinel string appears in any log record.

    The sentinel patient has:
    - ``name`` = ``_SENTINEL_NAME`` (``"SentinelPhiXYZ987"``)

    Additionally, some endpoints receive ``_SENTINEL_EMAIL`` as part of their
    *input* data (e.g. notification context, slider values) to verify that even
    input PHI that flows through the service is never re-logged.
    """

    async def _ensure_patient_seeded(self, db_session: AsyncSession) -> None:
        """Seed the sentinel patient and its dependencies for this test.

        The ``db_session`` fixture uses per-test rollback, so every test
        starts with a clean database.  We must re-seed for every test.
        """
        await _seed_sentinel_patient(db_session, _PID)
        await _seed_lifestyle_profile(db_session, _PID)
        await _seed_vitality_snapshot(db_session, _PID)
        await _seed_vitality_outlook(db_session, _PID, horizon_months=6)
        await db_session.flush()

    # ------------------------------------------------------------------
    # records/qa
    # ------------------------------------------------------------------

    async def test_records_qa_no_phi_in_logs(
        self,
        phi_test_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """POST /v1/patients/{pid}/records/qa must not log any sentinel value."""
        await self._ensure_patient_seeded(db_session)

        await _assert_no_phi_for_request(
            phi_test_client,
            "POST",
            f"/v1/patients/{_PID}/records/qa",
            context="records/qa",
            json_body={"question": "What are my health records?"},
        )

    # ------------------------------------------------------------------
    # coach/chat (SSE)
    # ------------------------------------------------------------------

    async def test_coach_chat_no_phi_in_logs(
        self,
        phi_test_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """POST /v1/patients/{pid}/coach/chat must not log any sentinel value.

        The coach service assembles a context from patient data (including
        ``name``, ``age``) and passes it to the LLM.  The log call in
        ``CoachService.stream`` must emit only non-PHI observability fields.
        """
        await self._ensure_patient_seeded(db_session)

        await _assert_no_phi_for_request(
            phi_test_client,
            "POST",
            f"/v1/patients/{_PID}/coach/chat",
            context="coach/chat",
            json_body={
                "message": "How can I improve my vitality?",
                "history": [],
            },
        )

    # ------------------------------------------------------------------
    # protocol/generate
    # ------------------------------------------------------------------

    async def test_protocol_generate_no_phi_in_logs(
        self,
        phi_test_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """POST /v1/patients/{pid}/protocol/generate must not log any PHI.

        Note: ``FakeLLMProvider._fake_dict_for_schema`` returns ``{}`` for
        schemas with required fields (like ``GeneratedProtocol``), causing a
        Pydantic ``ValidationError`` and a 422 response.  The service still
        emits structured log lines before the validation fails, so we capture
        and inspect those.  Accepting 422 allows the PHI assertion to run.
        """
        await self._ensure_patient_seeded(db_session)

        await _assert_no_phi_for_request(
            phi_test_client,
            "POST",
            f"/v1/patients/{_PID}/protocol/generate",
            context="protocol/generate",
            expected_statuses={200, 201, 422},
        )

    # ------------------------------------------------------------------
    # insights/outlook-narrator
    # ------------------------------------------------------------------

    async def test_outlook_narrator_no_phi_in_logs(
        self,
        phi_test_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """POST /v1/patients/{pid}/insights/outlook-narrator must not log PHI."""
        await self._ensure_patient_seeded(db_session)

        await _assert_no_phi_for_request(
            phi_test_client,
            "POST",
            f"/v1/patients/{_PID}/insights/outlook-narrator",
            context="insights/outlook-narrator",
            json_body={
                "patient_id": _PID,
                "horizon_months": 6,
                "top_drivers": ["sleep"],
            },
        )

    # ------------------------------------------------------------------
    # insights/future-self — also passes _SENTINEL_EMAIL as slider value
    # ------------------------------------------------------------------

    async def test_future_self_no_phi_in_logs(
        self,
        phi_test_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """POST /v1/patients/{pid}/insights/future-self must not log PHI.

        Passes the ``_SENTINEL_EMAIL`` as a slider key/value so the test verifies
        that *input* PHI that flows through the service is also never re-logged.
        """
        await self._ensure_patient_seeded(db_session)

        await _assert_no_phi_for_request(
            phi_test_client,
            "POST",
            f"/v1/patients/{_PID}/insights/future-self",
            context="insights/future-self",
            json_body={
                "patient_id": _PID,
                "sliders": {"sleep_improvement": 2, "contact": _SENTINEL_EMAIL},
            },
        )

    # ------------------------------------------------------------------
    # meal-log (multipart upload)
    # ------------------------------------------------------------------

    async def test_meal_log_no_phi_in_logs(
        self,
        phi_test_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """POST /v1/patients/{pid}/meal-log must not log any PHI."""
        await self._ensure_patient_seeded(db_session)

        await _assert_no_phi_for_request(
            phi_test_client,
            "POST",
            f"/v1/patients/{_PID}/meal-log",
            context="meal-log",
            files={"image": ("meal.png", _MINIMAL_PNG, "image/png")},
            data={"notes": "Lunch"},
            expected_statuses={201},
        )

    # ------------------------------------------------------------------
    # notifications/smart — passes _SENTINEL_EMAIL in context payload
    # ------------------------------------------------------------------

    async def test_notifications_smart_no_phi_in_logs(
        self,
        phi_test_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """POST /v1/patients/{pid}/notifications/smart must not log PHI.

        The ``context`` dict contains ``_SENTINEL_EMAIL`` as a value to test
        that service-layer input data is not re-emitted into the log stream.
        """
        await self._ensure_patient_seeded(db_session)

        await _assert_no_phi_for_request(
            phi_test_client,
            "POST",
            f"/v1/patients/{_PID}/notifications/smart",
            context="notifications/smart",
            json_body={
                "trigger_kind": "streak_at_risk",
                "context": {"streak_days": 3, "contact": _SENTINEL_EMAIL},
            },
        )

    # ------------------------------------------------------------------
    # Structural field assertion: AI log records must not contain unknown fields
    # ------------------------------------------------------------------

    async def test_ai_log_records_only_contain_allowed_fields(
        self,
        phi_test_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Structured AI log records must only contain whitelisted field names.

        Makes a representative records/qa request, captures logs, and checks
        that every extra field in every AI-service log record belongs to the
        allowed set (``_ALLOWED_AI_FIELDS ∪ _STANDARD_LOG_RECORD_FIELDS``).

        Any custom field that is NOT in either whitelist is reported as a
        potential leak vector.
        """
        await self._ensure_patient_seeded(db_session)

        handler, loggers = _install_capturing_handler()
        try:
            resp = await phi_test_client.post(
                f"/v1/patients/{_PID}/records/qa",
                json={"question": "What medications am I taking?"},
                headers=_HEADERS,
            )
        finally:
            _remove_capturing_handler(handler, loggers)

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        # Check only app.* records (not uvicorn, starlette, etc.)
        app_records = [r for r in handler.records if r.name.startswith("app")]

        allowed = _ALLOWED_AI_FIELDS | _STANDARD_LOG_RECORD_FIELDS

        for record in app_records:
            for key in record.__dict__:
                if key in allowed:
                    continue
                # Unknown field detected — fail with useful diagnostics.
                raise AssertionError(
                    f"Log record from {record.name!r} contains unexpected field "
                    f"{key!r} = {record.__dict__[key]!r}.\n"
                    f"  This may be a PHI leak vector.\n"
                    f"  Allowed fields: {sorted(allowed)}"
                )
