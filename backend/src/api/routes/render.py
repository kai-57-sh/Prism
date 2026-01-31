"""
Render API Routes - Trigger video generation for an existing planned job
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.models import get_db
from src.services.observability import logger
from src.api.routes.generation import GenerationResponse
from src.services.job_state import transition_state, JobStateError
from src.services.storage import JobDB
from src.config.constants import JOB_TIMEOUT_MINUTES
from src.services.rate_limiter import RateLimiter
from src.workers.queue import get_queue
from src.workers.render_tasks import run_render_job


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

        job = JobDB.get_job(db, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        if job.state in {"RUNNING", "SUBMITTED"}:
            raise ValueError("Job is already running or queued")
        if job.state == "FAILED":
            raise ValueError("Job is in FAILED state")
        if not job.shot_requests:
            raise ValueError("Job is missing shot requests")
        if job.shot_assets:
            raise ValueError("Job already has generated assets")

        rate_limiter = RateLimiter()
        rate_limit_result = rate_limiter.check_rate_limit(client_ip)
        if not rate_limit_result["allowed"]:
            raise ValueError(f"Rate limit exceeded. Try again at {rate_limit_result['reset_at']}")

        concurrent_result = rate_limiter.check_concurrent_jobs(client_ip)
        if not concurrent_result["allowed"]:
            raise ValueError(
                f"Concurrent job limit reached. Current: {concurrent_result['current']}, "
                f"Max: {concurrent_result['max']}"
            )

        try:
            queued_job = transition_state(db, job.job_id, "SUBMITTED", "generation_queued")
            if not queued_job:
                raise ValueError(f"Job {job_id} not found")
            job = queued_job
        except JobStateError as exc:
            raise ValueError(str(exc)) from exc

        queue = get_queue()
        rq_job = queue.enqueue(
            run_render_job,
            job.job_id,
            client_ip,
            job_timeout=JOB_TIMEOUT_MINUTES * 60,
        )

        logger.info(
            "render_queued",
            job_id=job.job_id,
            rq_job_id=rq_job.id,
            queue=queue.name,
        )

        return GenerationResponse(
            job_id=job.job_id,
            status=job.state,
            message="Generation queued. Use GET /v1/t2v/jobs/{job_id} to track progress.",
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
