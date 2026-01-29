"""
Revise API Routes - Iterative refinement workflow
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from src.models import get_db
from src.services.storage import JobDB
from src.services.job_manager import JobManager
from src.services.observability import logger
from src.core.llm_orchestrator import FeedbackParser
from src.core.validator import Validator


# Request/Response Models


class ReviseRequest(BaseModel):
    """Request for job revision"""

    feedback: str = Field(
        ...,
        description="User's feedback for revision",
        example="less camera shake, shorter narration",
        min_length=5,
        max_length=500,
    )


class ReviseResponse(BaseModel):
    """Response for revision request"""

    job_id: str
    parent_job_id: str
    status: str
    message: str
    targeted_fields: List[str]


# Router
router = APIRouter()


@router.post("/jobs/{job_id}/revise", response_model=ReviseResponse, status_code=status.HTTP_202_ACCEPTED)
async def revise_job(
    job_id: str,
    request: ReviseRequest,
    db: Session = Depends(get_db),
):
    """
    Revise video based on user feedback

    Creates a new job with targeted modifications while preserving
    non-targeted context to avoid topic drift.

    Args:
        job_id: Original job identifier
        request: Revision request with feedback
        db: Database session

    Returns:
        ReviseResponse with new job_id and targeted fields
    """
    try:
        # Get parent job from database
        parent_job = JobDB.get_job(db, job_id)

        if not parent_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "JOB_NOT_FOUND",
                        "message": f"Job {job_id} not found",
                    }
                }
            )

        # Validate parent job state
        if parent_job.state != "SUCCEEDED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_JOB_STATE",
                        "message": f"Job must be in SUCCEEDED state to revise, current state: {parent_job.state}",
                    }
                }
            )

        logger.info(
            "revise_request",
            parent_job_id=job_id,
            feedback=request.feedback[:100],  # Truncate for logging
        )

        # Parse feedback to identify targeted fields
        feedback_parser = FeedbackParser()
        feedback_result = feedback_parser.parse_feedback(
            feedback=request.feedback,
            previous_ir=parent_job.ir,
        )

        targeted_fields = feedback_result.get("targeted_fields", [])
        suggested_modifications = feedback_result.get("suggested_modifications", {})

        logger.info(
            "feedback_parsed",
            parent_job_id=job_id,
            targeted_fields=targeted_fields,
            suggested_modifications=suggested_modifications,
        )

        # Validate refinement
        validator = Validator()
        is_valid, error_msg = validator.validate_refinement(
            feedback=request.feedback,
            targeted_fields=targeted_fields,
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_REFINEMENT",
                        "message": error_msg,
                    }
                }
            )

        # Create job manager and execute revision workflow
        job_manager = JobManager()

        # Execute revision workflow
        revised_job = await job_manager.execute_revision_workflow(
            db=db,
            parent_job_id=job_id,
            feedback=request.feedback,
            targeted_fields=targeted_fields,
            suggested_modifications=suggested_modifications,
            client_ip=None,  # TODO: Extract from request
        )

        return ReviseResponse(
            job_id=revised_job.job_id,
            parent_job_id=job_id,
            status=revised_job.state,
            message="Revision job created. Use GET /v1/t2v/jobs/{job_id} to track progress.",
            targeted_fields=targeted_fields,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "revise_error",
            parent_job_id=job_id,
            error=str(e),
            error_type=type(e).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "REVISION_ERROR",
                    "message": "An error occurred during revision",
                }
            }
        )
