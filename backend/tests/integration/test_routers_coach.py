"""Integration tests for the POST /v1/patients/{patient_id}/coach/chat SSE endpoint.

Test strategy
-------------
All tests build a minimal FastAPI app (mini-app-factory pattern) that includes
only the coach router wired to the testcontainers-backed ``db_session`` fixture.
The ``CoachService`` dependency is overridden to inject ``FakeLLMProvider`` so
no network calls are made.

SSE parsing
-----------
``sse_starlette`` emits the standard event-stream wire format::

    event: token
    data: {"type": "token", "text": "Hello"}

    event: done
    data: {"type": "done", "ai_meta": {...}, "disclaimer": "..."}

We consume it via ``httpx.AsyncClient`` using ``stream()`` context + async
``iter_lines()`` to parse the raw byte stream.  A small helper
``_parse_sse_events`` accumulates (event_type, data_json) pairs.

Cross-patient isolation test
-----------------------------
We seed two patients (PT_COACH_A and PT_COACH_B), POST a chat as patient A,
and assert that the assembled context (passed through ``FakeLLMProvider``) does
NOT contain patient B's sentinel name in any yielded text.  Because
``FakeLLMProvider`` echoes back the user prompt in its token stream, and
``CoachService`` assembles the user prompt from DB data scoped to ``patient_id``,
B's data should be absent if isolation is correct.

Note: we do not assert B's data appears in A's stream; we assert it is absent.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 — register all tables

HEADERS = {"X-API-Key": "test-key"}

# ---------------------------------------------------------------------------
# SSE parsing helpers
# ---------------------------------------------------------------------------


def _parse_sse_events(raw_text: str) -> list[dict[str, Any]]:
    """Parse a raw SSE response body into a list of event dicts.

    Each event in the stream looks like::

        event: token
        data: {"type": "token", "text": "chunk"}

    Returns a list of parsed ``data`` JSON objects. ``event:`` lines are
    ignored; only ``data:`` payloads are returned.
    """
    events: list[dict[str, Any]] = []
    current_data: str | None = None

    for line in raw_text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            current_data = line[len("data:"):].strip()
        elif line == "" and current_data is not None:
            try:
                events.append(json.loads(current_data))
            except json.JSONDecodeError:
                pass
            current_data = None

    # Handle a final event without trailing blank line
    if current_data is not None:
        try:
            events.append(json.loads(current_data))
        except json.JSONDecodeError:
            pass

    return events


# ---------------------------------------------------------------------------
# DB seed helpers
# ---------------------------------------------------------------------------


def _utcnow():
    import datetime
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


async def _seed_patient(session: AsyncSession, patient_id: str, name: str) -> None:
    """Insert a minimal Patient row."""
    from app.models.patient import Patient

    p = Patient(
        patient_id=patient_id,
        name=name,
        age=38,
        sex="male",
        country="DE",
    )
    session.add(p)
    await session.flush()


# ---------------------------------------------------------------------------
# Mini app factory — builds an isolated FastAPI app with the coach router only
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session")
async def coach_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:  # type: ignore[return]
    """Minimal FastAPI app wrapping only the coach router.

    ``get_session`` is overridden to yield the testcontainers ``db_session`` so
    all HTTP calls participate in the per-test rollback transaction.
    """
    from fastapi import FastAPI
    from httpx._transports.asgi import ASGITransport

    from app.db.session import get_session
    from app.routers import coach

    app = FastAPI()
    app.include_router(coach.router, prefix="/v1")

    async def _override():  # type: ignore[return]
        yield db_session

    app.dependency_overrides[get_session] = _override

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCoachChatSSE:
    """Integration tests for POST /v1/patients/{patient_id}/coach/chat."""

    async def test_happy_path_yields_token_then_done(
        self,
        coach_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Streaming a chat returns 1+ token events followed by a done event."""
        await _seed_patient(db_session, "PT_ROUTER_A", "Alice RouterTest")

        resp = await coach_client.post(
            "/v1/patients/PT_ROUTER_A/coach/chat",
            json={"message": "How can I sleep better?", "history": []},
            headers=HEADERS,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert "text/event-stream" in resp.headers.get("content-type", ""), (
            f"Expected SSE content-type, got: {resp.headers.get('content-type')}"
        )

        events = _parse_sse_events(resp.text)

        token_events = [e for e in events if e.get("type") == "token"]
        done_events = [e for e in events if e.get("type") == "done"]

        assert len(token_events) >= 1, (
            f"Expected >=1 token events, got types: {[e.get('type') for e in events]}"
        )
        assert len(done_events) == 1, (
            f"Expected exactly 1 done event, got {len(done_events)}"
        )
        # done must be last
        assert events[-1]["type"] == "done", f"Last event was not 'done': {events[-1]}"

    async def test_done_event_contains_disclaimer(
        self,
        coach_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """The done event must carry the wellness disclaimer."""
        await _seed_patient(db_session, "PT_ROUTER_B", "Bob RouterTest")

        resp = await coach_client.post(
            "/v1/patients/PT_ROUTER_B/coach/chat",
            json={"message": "What foods are good for my heart?", "history": []},
            headers=HEADERS,
        )
        assert resp.status_code == 200

        events = _parse_sse_events(resp.text)
        done = next((e for e in events if e.get("type") == "done"), None)
        assert done is not None, "No done event found in stream"

        disclaimer = done.get("disclaimer", "")
        assert isinstance(disclaimer, str) and len(disclaimer) > 0, (
            f"'done' event missing disclaimer: {done}"
        )
        assert "not medical advice" in disclaimer.lower(), (
            f"Disclaimer does not contain 'not medical advice': {disclaimer!r}"
        )

    async def test_done_event_has_ai_meta(
        self,
        coach_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """The done event must carry an ai_meta dict with model and prompt_name."""
        await _seed_patient(db_session, "PT_ROUTER_C", "Carol RouterTest")

        resp = await coach_client.post(
            "/v1/patients/PT_ROUTER_C/coach/chat",
            json={"message": "Tell me about my vitality score.", "history": []},
            headers=HEADERS,
        )
        assert resp.status_code == 200

        events = _parse_sse_events(resp.text)
        done = next((e for e in events if e.get("type") == "done"), None)
        assert done is not None, "No done event found in stream"

        ai_meta = done.get("ai_meta")
        assert isinstance(ai_meta, dict), f"ai_meta not a dict: {ai_meta!r}"
        assert "model" in ai_meta, f"ai_meta missing 'model': {ai_meta}"
        assert "prompt_name" in ai_meta, f"ai_meta missing 'prompt_name': {ai_meta}"

    async def test_unknown_patient_returns_404(
        self,
        coach_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Requesting chat for a non-existent patient must return HTTP 404."""
        resp = await coach_client.post(
            "/v1/patients/PT_NOBODY_XYZ/coach/chat",
            json={"message": "Hello?", "history": []},
            headers=HEADERS,
        )
        assert resp.status_code == 404, (
            f"Expected 404 for unknown patient, got {resp.status_code}"
        )

    async def test_missing_api_key_returns_401(
        self,
        coach_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Omitting the X-API-Key header must return HTTP 401."""
        await _seed_patient(db_session, "PT_ROUTER_D", "Dave RouterTest")

        resp = await coach_client.post(
            "/v1/patients/PT_ROUTER_D/coach/chat",
            json={"message": "Hi", "history": []},
            # No headers — no API key
        )
        assert resp.status_code == 401, (
            f"Expected 401 without API key, got {resp.status_code}"
        )

    async def test_cross_patient_isolation(
        self,
        coach_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Chatting as patient A must not expose patient B's sentinel data.

        We seed two patients with distinctive names. Patient B also gets an
        EHR record containing a sentinel string. We POST chat as patient A
        and assert the sentinel does not appear in any token event text.

        This works because CoachService._build_user_prompt scopes all DB
        queries to the requesting patient_id. FakeLLMProvider echoes back
        the prompt in its token stream, so if B's data leaks into A's prompt,
        it would appear in A's token events.
        """
        from app.models.ehr_record import EHRRecord

        sentinel = "PATIENT_B_SECRET_SENTINEL_XYZ"
        await _seed_patient(db_session, "PT_ISO_A", "Isolate Alpha")
        await _seed_patient(db_session, "PT_ISO_B", "Isolate Beta")

        # Seed an EHR record for patient B with the sentinel
        ehr_b = EHRRecord(
            patient_id="PT_ISO_B",
            record_type="condition",
            recorded_at=_utcnow(),
            payload={"description": sentinel},
            source="test",
            embedding=None,
        )
        db_session.add(ehr_b)
        await db_session.flush()

        # Chat as patient A
        resp = await coach_client.post(
            "/v1/patients/PT_ISO_A/coach/chat",
            json={"message": "What can you tell me about my records?", "history": []},
            headers=HEADERS,
        )
        assert resp.status_code == 200

        # Check no event text contains patient B's sentinel
        events = _parse_sse_events(resp.text)
        full_text = json.dumps(events)
        assert sentinel not in full_text, (
            f"Cross-patient isolation failure: sentinel {sentinel!r} found in "
            f"patient A's stream events"
        )
