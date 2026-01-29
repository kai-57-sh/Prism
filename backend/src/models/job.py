"""
Job Model
"""

import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, JSON, DateTime, Index
from typing import Optional, List

from src.models import Base


class JobState(str, Enum):
    """Job lifecycle states"""

    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class JobModel(Base):
    """
    Job - Lifecycle and result tracking for a single user request

    Manages per-shot generation workflow with ffmpeg post-processing
    for video/audio separation.
    """

    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)

    # Public job identifier
    job_id = Column(String, unique=True, nullable=False, index=True)

    # User input (PII redacted)
    user_input_redacted = Column(String, nullable=False)
    user_input_hash = Column(String, nullable=False, index=True)
    pii_flags = Column(JSON, nullable=True)  # List of detected PII categories

    # Template reference
    template_id = Column(String, nullable=False, index=True)
    template_version = Column(String, nullable=False)

    # Quality mode
    quality_mode = Column(String, nullable=False)  # "fast", "balanced", "high"

    # Job state
    state = Column(String, nullable=False, index=True)  # CREATED, SUBMITTED, RUNNING, SUCCEEDED, FAILED
    clarification_state = Column(String, nullable=True)  # "pending", "clarified", "waived"
    clarification_required_fields = Column(JSON, nullable=True)  # Fields requiring clarification

    # Intermediate data
    ir = Column(JSON, nullable=False)  # Complete Intermediate Representation
    shot_plan = Column(JSON, nullable=False)  # Complete Shot Plan

    # Per-shot generation data
    shot_requests = Column(JSON, nullable=False)  # Per-shot compiled prompts and params
    shot_assets = Column(JSON, nullable=True)  # Per-shot video/audio assets
    preview_shot_assets = Column(JSON, nullable=True)  # Preview candidates per shot
    selected_seeds = Column(JSON, nullable=True)  # User-selected seeds per shot

    # External task IDs
    external_task_ids = Column(JSON, nullable=False)  # DashScope task IDs per shot

    # Output metadata
    total_duration_s = Column(Integer, nullable=False)
    resolution = Column(String, nullable=False)  # "1280x720" or "1920x1080"

    # Error handling
    error_details = Column(JSON, nullable=True)  # {"code": "ERROR_CODE", "message": "...", "classification": "retryable/non_retryable"}

    # State transitions
    state_transitions = Column(JSON, nullable=False)  # [{"state": "CREATED", "timestamp": "...", "event": "job_created"}]

    # Retry tracking
    retry_count = Column(Integer, default=0, nullable=False)
    last_retry_error = Column(JSON, nullable=True)  # Last error details
    retry_exhausted = Column(JSON, nullable=True)  # Boolean flag

    # Revision tracking
    revision_of = Column(String, nullable=True, index=True)  # Parent job_id if this is a revision
    targeted_fields = Column(JSON, nullable=True)  # Fields modified in revision

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    running_at = Column(DateTime, nullable=True)
    succeeded_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_job_id", "job_id"),
        Index("idx_state", "state"),
        Index("idx_created_at", "created_at"),
        Index("idx_user_input_hash", "user_input_hash"),
    )

    def to_dict(self) -> dict:
        """Convert job model to dictionary"""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "user_input_redacted": self.user_input_redacted,
            "user_input_hash": self.user_input_hash,
            "pii_flags": self.pii_flags,
            "template_id": self.template_id,
            "template_version": self.template_version,
            "quality_mode": self.quality_mode,
            "state": self.state,
            "clarification_state": self.clarification_state,
            "clarification_required_fields": self.clarification_required_fields,
            "ir": self.ir,
            "shot_plan": self.shot_plan,
            "shot_requests": self.shot_requests,
            "shot_assets": self.shot_assets,
            "preview_shot_assets": self.preview_shot_assets,
            "selected_seeds": self.selected_seeds,
            "external_task_ids": self.external_task_ids,
            "total_duration_s": self.total_duration_s,
            "resolution": self.resolution,
            "error_details": self.error_details,
            "state_transitions": self.state_transitions,
            "retry_count": self.retry_count,
            "last_retry_error": self.last_retry_error,
            "retry_exhausted": self.retry_exhausted,
            "revision_of": self.revision_of,
            "targeted_fields": self.targeted_fields,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "running_at": self.running_at.isoformat() if self.running_at else None,
            "succeeded_at": self.succeeded_at.isoformat() if self.succeeded_at else None,
            "failed_at": self.failed_at.isoformat() if self.failed_at else None,
        }

    @property
    def input_hash(self) -> str:
        """Compatibility alias for user_input_hash."""
        return self.user_input_hash

    @input_hash.setter
    def input_hash(self, value: str) -> None:
        self.user_input_hash = value

    @staticmethod
    def generate_job_id() -> str:
        """Generate a unique job ID"""
        return str(uuid.uuid4())
