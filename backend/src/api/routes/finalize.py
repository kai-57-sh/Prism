"""
Finalize API Routes - Preview to Final workflow
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from src.models import get_db
from src.services.storage import JobDB
from src.services.job_manager import JobManager
from src.services.observability import logger
from src.config.constants import SUPPORTED_RESOLUTIONS


# Request/Response Models


class FinalizeRequest(BaseModel):
    """Request to finalize job with selected preview candidates"""

    selected_seeds: Dict[int, int] = Field(
        ...,
        description="Mapping of shot_id to selected seed for finalization",
        example={1: 12345, 2: 67890},
    )

    @classmethod
    def validate_seeds(cls, v, job):
        """Validate that selected seeds exist in preview assets"""
        if not job.preview_shot_assets:
            raise ValueError("No preview assets available for finalization")

        available_shot_ids = {asset["shot_id"] for asset in job.preview_shot_assets}
        selected_shot_ids = set(v.keys())

        if not selected_shot_ids.issubset(available_shot_ids):
            invalid = selected_shot_ids - available_shot_ids
            raise ValueError(f"Invalid shot_ids: {invalid}")

        # Validate seeds are available
        for shot_id, seed in v.items():
            shot_assets = [
                asset for asset in job.preview_shot_assets
                if asset["shot_id"] == shot_id
            ]

            available_seeds = {asset["seed"] for asset in shot_assets}
            if seed not in available_seeds:
                raise ValueError(f"Seed {seed} not available for shot {shot_id}")

        return v


class FinalizeResponse(BaseModel):
    """Response for finalize request"""

    job_id: str
    status: str
    message: str
    resolution: str


# Router
router = APIRouter()


@router.post("/jobs/{job_id}/finalize", response_model=FinalizeResponse, status_code=status.HTTP_202_ACCEPTED)
async def finalize_job(
    job_id: str,
    request: FinalizeRequest,
    db: Session = Depends(get_db),
):
    """
    Finalize job by regenerating selected shots at 1080P

    Args:
        job_id: Job identifier
        request: Finalization request with selected seeds
        db: Database session

    Returns:
        FinalizeResponse with job_id and status
    """
    try:
        # Get job from database
        job = JobDB.get_job(db, job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "JOB_NOT_FOUND",
                        "message": f"Job {job_id} not found",
                    }
                }
            )

        # Validate job state
        if job.state != "SUCCEEDED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_JOB_STATE",
                        "message": f"Job must be in SUCCEEDED state to finalize, current state: {job.state}",
                    }
                }
            )

        # Validate preview assets exist
        if not job.preview_shot_assets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "NO_PREVIEW_ASSETS",
                        "message": "No preview assets available for finalization",
                    }
                }
            )

        # Validate selected seeds
        try:
            FinalizeRequest.validate_seeds(request.selected_seeds, job)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_SEEDS",
                        "message": str(e),
                    }
                }
            )

        logger.info(
            "finalize_request",
            job_id=job_id,
            selected_seeds=request.selected_seeds,
        )

        # Create job manager and execute finalization
        job_manager = JobManager()

        # Execute finalization workflow
        finalized_job = await job_manager.execute_finalization_workflow(
            db=db,
            job_id=job_id,
            selected_seeds=request.selected_seeds,
            target_resolution="1920x1080",  # Always finalize at 1080P
        )

        return FinalizeResponse(
            job_id=finalized_job.job_id,
            status=finalized_job.state,
            message="Finalization started. Use GET /v1/t2v/jobs/{job_id} to track progress.",
            resolution="1920x1080",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "finalize_error",
            job_id=job_id,
            error=str(e),
            error_type=type(e).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "FINALIZATION_ERROR",
                    "message": "An error occurred during finalization",
                }
            }
        )
