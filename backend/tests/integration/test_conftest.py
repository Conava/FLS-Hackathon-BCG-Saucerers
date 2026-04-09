"""Integration tests that prove the per-test transaction rollback works.

These tests intentionally depend on execution order — test_db_session_rolled_back
must run *after* test_db_session_insert_visible_in_same_test — because the second
test proves that the row inserted in the first test was rolled back.

We rely on pytest's default alphabetical/declaration ordering within the same
module for this. Both tests are integration-level (real Postgres via testcontainers)
but do NOT require the compose stack, so they run in CI without extra flags.
"""

import pytest
from sqlmodel import select

from app.models import Patient


@pytest.mark.integration
async def test_db_session_insert_visible_in_same_test(db_session):
    """A row inserted within a test is visible to subsequent queries in the same test."""
    patient = Patient(
        patient_id="PT_CONFTEST_01",
        name="Conftest Test Patient",
        age=30,
        sex="M",
        country="DE",
    )
    db_session.add(patient)
    await db_session.flush()

    result = await db_session.execute(
        select(Patient).where(Patient.patient_id == "PT_CONFTEST_01")
    )
    found = result.scalar_one_or_none()
    assert found is not None, "Row inserted in same test must be visible after flush()"
    assert found.name == "Conftest Test Patient"


@pytest.mark.integration
async def test_db_session_rolled_back_between_tests(db_session):
    """The row from the previous test must be gone — proving per-test rollback."""
    result = await db_session.execute(
        select(Patient).where(Patient.patient_id == "PT_CONFTEST_01")
    )
    found = result.scalar_one_or_none()
    assert found is None, (
        "Row from previous test must not be present — per-test rollback is broken"
    )
