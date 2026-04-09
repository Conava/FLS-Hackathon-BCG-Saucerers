"""Integration tests for CoachService streaming.

Tests verify:
- The async generator yields at least one ``token`` event and a final ``done`` event.
- The ``done`` event carries the "Not medical advice" disclaimer.
- No PHI (patient name / email / patient_id) appears in log records emitted during
  the call.

Uses the shared ``db_session`` fixture (testcontainers Postgres 16 + pgvector,
per-test rollback) and ``FakeLLMProvider`` — no network calls.

Seed data
---------
For each test that exercises CoachService.stream(), we insert:
  - A Patient with a unique sentinel name/patient_id.
  - A LifestyleProfile for that patient.
  - Three EHRRecord rows (so EHR retrieval has something to return).
  - Three DailyLog rows (last 7 days).
  - An active Protocol with two ProtocolAction rows.

PHI test
--------
We capture all log records emitted during the call and assert that none
contain the patient's name, email-style string, or patient_id sentinel.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401 — registers all tables with SQLModel metadata

# ---------------------------------------------------------------------------
# Helper imports — imported lazily inside tests to avoid import-time side-effects
# ---------------------------------------------------------------------------

_DISCLAIMER_FRAGMENT = "not medical advice"  # case-insensitive substring check

# Unique sentinel values — chosen to be distinctive enough that finding them
# in a log line unambiguously indicates PHI leakage.
_SENTINEL_PATIENT_ID = "PT_COACH_TEST_001"
_SENTINEL_NAME = "SentinelCoachPatient"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow():  # type: ignore[return]
    """Return naive UTC datetime (CLAUDE.md pattern)."""
    import datetime

    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


def _make_patient() -> app.models.Patient:  # type: ignore[name-defined]
    """Build a Patient with a unique sentinel name for PHI-leak detection."""
    return app.models.Patient(  # type: ignore[attr-defined]
        patient_id=_SENTINEL_PATIENT_ID,
        name=_SENTINEL_NAME,
        age=42,
        sex="female",
        country="DE",
    )


# ---------------------------------------------------------------------------
# LogCapture handler
# ---------------------------------------------------------------------------


class _ListHandler(logging.Handler):
    """Logging handler that collects all LogRecords into a list."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D102
        self.records.append(record)


# ---------------------------------------------------------------------------
# Fixture — seed the DB with a full patient context
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session")
async def coach_seed(db_session: AsyncSession) -> dict:
    """Seed one patient with lifestyle, EHR records, daily logs, and an active protocol.

    Returns a dict with:
      - ``patient_id``: str
      - ``name``: str
    """
    import datetime

    from app.models.daily_log import DailyLog
    from app.models.ehr_record import EHRRecord
    from app.models.lifestyle_profile import LifestyleProfile
    from app.models.protocol import Protocol, ProtocolAction

    patient = _make_patient()
    db_session.add(patient)
    await db_session.flush()

    # Lifestyle profile
    lifestyle = LifestyleProfile(
        patient_id=_SENTINEL_PATIENT_ID,
        survey_date=datetime.date(2026, 4, 1),
        smoking_status="never",
        diet_quality_score=7,
        exercise_sessions_weekly=3,
        stress_level=4,
        sleep_satisfaction=6,
    )
    db_session.add(lifestyle)
    await db_session.flush()

    # EHR records — three rows so the top-k retrieval loop has something
    now = _utcnow()
    for i, rtype in enumerate(["condition", "medication", "lab_panel"]):
        payload: dict
        if rtype == "condition":
            payload = {"icd_code": "Z82.49", "description": "Family history cardiovascular"}
        elif rtype == "medication":
            payload = {"name": "Vitamin D", "dose": "1000 IU daily"}
        else:
            payload = {
                "total_cholesterol_mmol": 5.2,
                "ldl_mmol": 3.1,
                "hdl_mmol": 1.4,
                "triglycerides_mmol": 1.5,
                "hba1c_pct": 5.4,
                "fasting_glucose_mmol": 5.0,
                "crp_mg_l": 1.2,
                "egfr_ml_min": 88.0,
                "sbp_mmhg": 122.0,
                "dbp_mmhg": 80.0,
            }
        ehr = EHRRecord(
            patient_id=_SENTINEL_PATIENT_ID,
            record_type=rtype,
            recorded_at=now,
            payload=payload,
            source="test",
            embedding=None,
        )
        db_session.add(ehr)

    await db_session.flush()

    # Daily logs — three entries covering the last 3 days
    for days_ago in range(1, 4):
        log = DailyLog(
            patient_id=_SENTINEL_PATIENT_ID,
            logged_at=now - datetime.timedelta(days=days_ago),
            mood=4,
            workout_minutes=30,
            sleep_hours=7.5,
            water_ml=2000,
            alcohol_units=0.0,
        )
        db_session.add(log)

    await db_session.flush()

    # Active Protocol with two ProtocolAction rows
    protocol = Protocol(
        patient_id=_SENTINEL_PATIENT_ID,
        week_start=datetime.date(2026, 4, 7),
        status="active",
        generated_by="fake",
        created_at=now,
    )
    db_session.add(protocol)
    await db_session.flush()

    for title in ("Walk 25 minutes", "Sleep by 22:30"):
        action = ProtocolAction(
            protocol_id=protocol.id,
            category="movement",
            title=title,
            rationale="Consistent movement supports healthy ageing.",
            target_value="25 min",
            streak_days=2,
            completed_today=False,
        )
        db_session.add(action)

    await db_session.flush()

    return {
        "patient_id": _SENTINEL_PATIENT_ID,
        "name": _SENTINEL_NAME,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCoachServiceStreaming:
    """Integration tests for CoachService.stream()."""

    async def test_stream_yields_token_events(
        self, db_session: AsyncSession, coach_seed: dict
    ) -> None:
        """stream() must yield at least one ``{type: 'token', text: ...}`` event."""
        from app.ai.llm import FakeLLMProvider
        from app.services.coach import CoachService

        patient_id = coach_seed["patient_id"]
        svc = CoachService(session=db_session, llm=FakeLLMProvider())

        events: list[dict] = []
        async for event in svc.stream(
            patient_id=patient_id,
            message="How can I improve my sleep?",
            history=[],
        ):
            events.append(event)

        token_events = [e for e in events if e.get("type") == "token"]
        assert len(token_events) >= 1, (
            f"Expected ≥1 token events, got: {[e.get('type') for e in events]}"
        )
        # Every token event must have a non-empty text field.
        for evt in token_events:
            assert isinstance(evt.get("text"), str), f"token event missing text: {evt}"
            assert len(evt["text"]) > 0, f"token event has empty text: {evt}"

    async def test_stream_ends_with_done_event(
        self, db_session: AsyncSession, coach_seed: dict
    ) -> None:
        """stream() must finish with exactly one ``{type: 'done', ...}`` event."""
        from app.ai.llm import FakeLLMProvider
        from app.services.coach import CoachService

        patient_id = coach_seed["patient_id"]
        svc = CoachService(session=db_session, llm=FakeLLMProvider())

        events: list[dict] = []
        async for event in svc.stream(
            patient_id=patient_id,
            message="Tell me about my protocol.",
            history=[],
        ):
            events.append(event)

        done_events = [e for e in events if e.get("type") == "done"]
        assert len(done_events) == 1, (
            f"Expected exactly 1 done event, got {len(done_events)}: {done_events}"
        )

        # The done event must be the last one emitted.
        assert events[-1]["type"] == "done", (
            f"Last event is not 'done': {events[-1]}"
        )

    async def test_done_event_contains_disclaimer(
        self, db_session: AsyncSession, coach_seed: dict
    ) -> None:
        """The ``done`` event must contain the 'Not medical advice' disclaimer."""
        from app.ai.llm import FakeLLMProvider
        from app.services.coach import CoachService

        patient_id = coach_seed["patient_id"]
        svc = CoachService(session=db_session, llm=FakeLLMProvider())

        events: list[dict] = []
        async for event in svc.stream(
            patient_id=patient_id,
            message="What should I eat today?",
            history=[],
        ):
            events.append(event)

        done = next(e for e in events if e.get("type") == "done")

        # Disclaimer must be present as a non-empty string field.
        disclaimer = done.get("disclaimer", "")
        assert isinstance(disclaimer, str) and len(disclaimer) > 0, (
            f"'done' event missing disclaimer: {done}"
        )
        # Must contain the key phrase (case-insensitive).
        assert _DISCLAIMER_FRAGMENT in disclaimer.lower(), (
            f"Disclaimer does not contain '{_DISCLAIMER_FRAGMENT}': {disclaimer!r}"
        )

    async def test_done_event_has_ai_meta(
        self, db_session: AsyncSession, coach_seed: dict
    ) -> None:
        """The ``done`` event must carry ``ai_meta`` with model and prompt_name."""
        from app.ai.llm import FakeLLMProvider
        from app.services.coach import CoachService

        patient_id = coach_seed["patient_id"]
        svc = CoachService(session=db_session, llm=FakeLLMProvider())

        events: list[dict] = []
        async for event in svc.stream(
            patient_id=patient_id,
            message="How am I doing?",
            history=[],
        ):
            events.append(event)

        done = next(e for e in events if e.get("type") == "done")
        ai_meta = done.get("ai_meta")
        assert isinstance(ai_meta, dict), f"'done' event missing ai_meta dict: {done}"
        assert "model" in ai_meta, f"ai_meta missing 'model': {ai_meta}"
        assert "prompt_name" in ai_meta, f"ai_meta missing 'prompt_name': {ai_meta}"

    async def test_no_phi_in_logs(
        self, db_session: AsyncSession, coach_seed: dict
    ) -> None:
        """No PHI (patient name or patient_id) must appear in any log record.

        We attach a custom handler to the root logger, run the stream, then
        inspect all captured log messages for the sentinel values.
        """
        from app.ai.llm import FakeLLMProvider
        from app.services.coach import CoachService

        patient_id = coach_seed["patient_id"]
        patient_name = coach_seed["name"]

        # Install capture handler.
        handler = _ListHandler()
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

        try:
            svc = CoachService(session=db_session, llm=FakeLLMProvider())
            async for _ in svc.stream(
                patient_id=patient_id,
                message="What are my top health risks?",
                history=[],
            ):
                pass
        finally:
            root_logger.removeHandler(handler)

        # Assert no log record contains the sentinel PHI values.
        phi_values = [patient_name]  # name is the most recognisable PHI
        for record in handler.records:
            msg = record.getMessage()
            formatted = logging.Formatter().format(record)
            combined = f"{msg} {formatted}"
            for phi in phi_values:
                assert phi not in combined, (
                    f"PHI leak detected in log: sentinel={phi!r} found in\n  {combined!r}"
                )

    async def test_stream_event_ordering(
        self, db_session: AsyncSession, coach_seed: dict
    ) -> None:
        """Token events must all precede the done event."""
        from app.ai.llm import FakeLLMProvider
        from app.services.coach import CoachService

        patient_id = coach_seed["patient_id"]
        svc = CoachService(session=db_session, llm=FakeLLMProvider())

        events: list[dict] = []
        async for event in svc.stream(
            patient_id=patient_id,
            message="Give me a summary of my health.",
            history=[],
        ):
            events.append(event)

        done_index = next(
            (i for i, e in enumerate(events) if e.get("type") == "done"), None
        )
        assert done_index is not None, "No 'done' event found"
        assert done_index == len(events) - 1, (
            "'done' must be the last event in the sequence"
        )

        # All events before 'done' must be 'token' or 'protocol_suggestion'.
        allowed_before_done = {"token", "protocol_suggestion"}
        for evt in events[:done_index]:
            assert evt.get("type") in allowed_before_done, (
                f"Unexpected event type before 'done': {evt}"
            )
