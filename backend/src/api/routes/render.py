"""
Render API Routes - Trigger video generation for an existing planned job
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.models import get_db
from src.services.job_manager import JobManager
from src.services.observability import logger
from src.api.routes.generation import GenerationResponse


router = APIRouter()


@router.post("/jobs/{job_id}/render", response_model=GenerationResponse, status_code=status.HTTP_202_ACCEPTED)
async def render_job(
    job_id: str,
    http_request: Request,
    db: Session = Depends(get_db),
):
    """
    Trigger video generation for an existing planned job.
    """
    try:
        client_ip = http_request.client.host
        if "X-Forwarded-For" in http_request.headers:
            client_ip = http_request.headers["X-Forwarded-For"].split(",")[0].strip()

        logger.info(
            "render_request",
            job_id=job_id,
            client_ip=client_ip,
        )

        job_manager = JobManager()
        job = await job_manager.execute_generation_from_job(
            db=db,
            job_id=job_id,
            client_ip=client_ip,
        )

        return GenerationResponse(
            job_id=job.job_id,
            status=job.state,
            message="Generation started. Use GET /v1/t2v/jobs/{job_id} to track progress.",
        )

    except ValueError as e:
        logger.warning(
            "render_validation_failed",
            job_id=job_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "RENDER_ERROR",
                    "message": str(e),
                }
            }
        )

    except Exception as e:
        logger.error(
            "render_error",
            job_id=job_id,
            error=str(e),
            error_type=type(e).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "RENDER_ERROR",
                    "message": "An error occurred during generation",
                }
            }
        )
