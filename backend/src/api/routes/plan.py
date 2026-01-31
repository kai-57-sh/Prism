"""
Planning API Routes - Script and shot plan generation only
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.models import get_db
from src.services.job_manager import JobManager
from src.services.observability import logger
from src.api.routes.generation import GenerationRequest, GenerationResponse


router = APIRouter()


@router.post("/plan", response_model=GenerationResponse, status_code=status.HTTP_202_ACCEPTED)
async def plan_video(
    request: GenerationRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    """
    Create a job with script and shot plan only (no video generation).
    """
    try:
        client_ip = http_request.client.host
        if "X-Forwarded-For" in http_request.headers:
            client_ip = http_request.headers["X-Forwarded-For"].split(",")[0].strip()

        logger.info(
            "plan_request",
            user_prompt=request.user_prompt[:100],
            quality_mode=request.quality_mode,
            client_ip=client_ip,
        )

        job_manager = JobManager()
        job = await job_manager.execute_planning_workflow(
            db=db,
            user_input=request.user_prompt,
            quality_mode=request.quality_mode,
            client_ip=client_ip,
            resolution=request.resolution,
        )

        return GenerationResponse(
            job_id=job.job_id,
            status=job.state,
            message="Plan created successfully. Use GET /v1/t2v/jobs/{job_id} to review.",
        )

    except ValueError as e:
        error_msg = str(e)

        if "clarification" in error_msg.lower():
            logger.warning(
                "plan_clarification_required",
                error=error_msg,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "CLARIFICATION_REQUIRED",
                        "message": error_msg,
                    },
                    "clarification_required_fields": [],
                }
            )

        logger.warning(
            "plan_validation_failed",
            error=error_msg,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": error_msg,
                }
            }
        )

    except Exception as e:
        logger.error(
            "plan_error",
            error=str(e),
            error_type=type(e).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "PLANNING_ERROR",
                    "message": "An error occurred during planning",
                }
            }
        )
