"""
Job State Management Service
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from src.models.job import JobModel
from src.services.storage import JobDB


class JobStateError(Exception):
    """Exception raised for invalid state transitions"""

    pass


# Valid state transitions
VALID_TRANSITIONS = {
    "CREATED": ["SUBMITTED", "FAILED"],
    "SUBMITTED": ["RUNNING", "FAILED"],
    "RUNNING": ["SUCCEEDED", "FAILED"],
    "SUCCEEDED": ["RUNNING"],  # Allow finalization/revision workflows to restart
    "FAILED": [],  # Terminal state
}


def transition_state(
    db: Session,
    job_id: str,
    new_state: str,
    event: str,
) -> Optional[JobModel]:
    """
    Transition job to new state with validation

    Args:
        db: Database session
        job_id: Job identifier
        new_state: Target state (CREATED, SUBMITTED, RUNNING, SUCCEEDED, FAILED)
        event: Event triggering the transition

    Returns:
        Updated JobModel or None if job not found

    Raises:
        JobStateError: If transition is invalid
    """
    job = JobDB.get_job(db, job_id)
    if not job:
        return None

    current_state = job.state

    # Validate state transition
    if new_state not in VALID_TRANSITIONS.get(current_state, []):
        raise JobStateError(
            f"Invalid state transition: {current_state} -> {new_state}. "
            f"Valid transitions from {current_state}: {VALID_TRANSITIONS.get(current_state, [])}"
        )

    # Update job state
    updated_job = JobDB.update_job_state(
        db=db,
        job_id=job_id,
        new_state=new_state,
        event=event,
        timestamp=datetime.utcnow(),
    )

    return updated_job


def get_current_state(db: Session, job_id: str) -> Optional[str]:
    """
    Get current state of a job

    Args:
        db: Database session
        job_id: Job identifier

    Returns:
        Current state or None if job not found
    """
    job = JobDB.get_job(db, job_id)
    return job.state if job else None


def is_terminal_state(state: str) -> bool:
    """
    Check if state is a terminal state

    Args:
        state: Job state

    Returns:
        True if state is SUCCEEDED or FAILED
    """
    return state in ["SUCCEEDED", "FAILED"]
