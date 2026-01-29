"""
Unit Tests for Job State Transitions
"""

import pytest

from src.services.job_state import (
    JobStateError,
    get_current_state,
    is_terminal_state,
    transition_state,
)
from src.services.storage import JobDB


def _create_job(db):
    return JobDB.create_job(
        db=db,
        user_input_redacted="test",
        user_input_hash="hash",
        template_id="template",
        template_version="1.0",
        quality_mode="balanced",
        ir={},
        shot_plan={},
        shot_requests=[],
        external_task_ids=[],
        total_duration_s=3,
        resolution="1280x720",
    )


def test_transition_state_valid(test_db_session):
    """Valid transition updates state and transitions list."""
    job = _create_job(test_db_session)

    updated = transition_state(test_db_session, job.job_id, "SUBMITTED", "submitted")

    assert updated is not None
    assert updated.state == "SUBMITTED"
    assert updated.state_transitions[-1]["event"] == "submitted"


def test_transition_state_invalid(test_db_session):
    """Invalid transition raises JobStateError."""
    job = _create_job(test_db_session)

    with pytest.raises(JobStateError):
        transition_state(test_db_session, job.job_id, "SUCCEEDED", "invalid")


def test_get_current_state(test_db_session):
    """Current state is returned for existing jobs."""
    job = _create_job(test_db_session)

    state = get_current_state(test_db_session, job.job_id)
    assert state == "CREATED"


def test_is_terminal_state():
    """Terminal state detection."""
    assert is_terminal_state("SUCCEEDED")
    assert is_terminal_state("FAILED")
    assert not is_terminal_state("RUNNING")
