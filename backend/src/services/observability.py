"""
Observability and Logging Service
"""

import structlog
from typing import Dict, Any, Optional
from datetime import datetime

from src.config.settings import settings


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Get logger
logger = structlog.get_logger(__name__)


def log_template_hit(
    template_id: str,
    confidence: float,
    confidence_components: Dict[str, float],
    job_id: Optional[str] = None,
) -> None:
    """
    Log template match event

    Args:
        template_id: Matched template ID
        confidence: Confidence score [0, 1]
        confidence_components: {"embedding": 0.7, "tags": 0.3}
        job_id: Optional job ID for context
    """
    log_data = {
        "template_id": template_id,
        "confidence": confidence,
        "confidence_components": confidence_components,
    }
    if job_id:
        log_data["job_id"] = job_id

    logger.info("template_matched", **log_data)


def log_clarification_trigger(
    required_fields: list,
    reason: str,
    job_id: Optional[str] = None,
) -> None:
    """
    Log clarification required event

    Args:
        required_fields: List of fields requiring clarification
        reason: Reason clarification is needed
        job_id: Optional job ID for context
    """
    log_data = {
        "required_fields": required_fields,
        "reason": reason,
    }
    if job_id:
        log_data["job_id"] = job_id

    logger.warning("clarification_triggered", **log_data)


def log_failure_classification(
    error_code: str,
    classification: str,
    retryable: bool,
    job_id: Optional[str] = None,
) -> None:
    """
    Log failure classification event

    Args:
        error_code: Error code (e.g., "DASHSCOPE_TIMEOUT", "FFMPEG_ERROR")
        classification: Error classification ("retryable" or "non_retryable")
        retryable: Whether error is retryable
        job_id: Optional job ID for context
    """
    log_data = {
        "error_code": error_code,
        "classification": classification,
        "retryable": retryable,
    }
    if job_id:
        log_data["job_id"] = job_id

    logger.error("failure_classified", **log_data)


def log_generation_duration(
    job_id: str,
    duration_s: float,
    shot_count: int,
    quality_mode: str,
) -> None:
    """
    Log video generation duration

    Args:
        job_id: Job ID
        duration_s: Total duration in seconds
        shot_count: Number of shots generated
        quality_mode: Quality mode used
    """
    logger.info(
        "generation_completed",
        job_id=job_id,
        duration_s=duration_s,
        shot_count=shot_count,
        quality_mode=quality_mode,
        avg_duration_per_shot=duration_s / shot_count if shot_count > 0 else 0,
    )


def log_revision_event(
    job_id: str,
    parent_job_id: str,
    targeted_fields: list,
) -> None:
    """
    Log job revision event

    Args:
        job_id: New revision job ID
        parent_job_id: Original job ID
        targeted_fields: Fields modified in revision
    """
    logger.info(
        "job_revised",
        job_id=job_id,
        parent_job_id=parent_job_id,
        targeted_fields=targeted_fields,
    )


def log_quality_mode_stats(
    quality_mode: str,
    preview_count: int,
    final_count: int,
) -> None:
    """
    Log quality mode usage statistics

    Args:
        quality_mode: Quality mode (fast, balanced, high)
        preview_count: Number of preview generations
        final_count: Number of final generations
    """
    logger.info(
        "quality_mode_stats",
        quality_mode=quality_mode,
        preview_count=preview_count,
        final_count=final_count,
    )
