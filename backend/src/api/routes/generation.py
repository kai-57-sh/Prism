"""
Generation API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, ValidationInfo, field_validator
from typing import Optional, List
from sqlalchemy.orm import Session

from src.models import get_db
from src.services.job_manager import JobManager
from src.services.storage import JobDB
from src.services.observability import logger
from src.config.constants import SUPPORTED_LANGUAGES


# Request/Response Models


class GenerationRequest(BaseModel):
    """Request for video generation"""

    user_prompt: str = Field(..., description="User's text description of the desired video")
    quality_mode: str = Field(default="balanced", description="Quality mode: fast, balanced, or high")
    duration_preference_s: Optional[int] = Field(None, ge=2, le=15, description="Preferred total duration in seconds")
    resolution: str = Field(default="1280x720", description="Video resolution: 1280x720 or 1920x1080")

    # Unsupported fields (rejected with error)
    audio_url: Optional[str] = None
    audio_file: Optional[str] = None
    audio_upload: Optional[str] = None

    @field_validator("quality_mode")
    @classmethod
    def validate_quality_mode(cls, v):
        if v not in ["fast", "balanced", "high"]:
            raise ValueError("quality_mode must be one of: fast, balanced, high")
        return v

    @field_validator("resolution")
    @classmethod
    def validate_resolution(cls, v):
        if v in ["1280*720", "1920*1080"]:
            v = v.replace("*", "x")
        if v not in ["1280x720", "1920x1080"]:
            raise ValueError("resolution must be 1280x720 or 1920x1080")
        return v

    @field_validator("audio_url", "audio_file", "audio_upload")
    @classmethod
    def validate_audio_fields(cls, v, info: ValidationInfo):
        if v is not None:
            raise ValueError(f"{info.field_name} is not supported in this version")
        return None


class GenerationResponse(BaseModel):
    """Response for generation request"""

    job_id: str
    status: str
    message: str


class ClarificationRequiredResponse(BaseModel):
    """Response when clarification is required"""

    error: dict
    clarification_required_fields: List[str]


# Router
router = APIRouter()


@router.post("/generate", response_model=GenerationResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_video(
    request: GenerationRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    """
    Submit video generation request

    Args:
        request: Generation request
        http_request: FastAPI request for IP extraction
        db: Database session

    Returns:
        GenerationResponse with job_id
    """
    try:
        # Get client IP
        client_ip = http_request.client.host
        if "X-Forwarded-For" in http_request.headers:
            client_ip = http_request.headers["X-Forwarded-For"].split(",")[0].strip()

        logger.info(
            "generate_request",
            user_prompt=request.user_prompt[:100],  # Truncate for logging
            quality_mode=request.quality_mode,
            client_ip=client_ip,
        )

        # Create job manager
        job_manager = JobManager()

        # Execute workflow
        job = await job_manager.execute_generation_workflow(
            db=db,
            user_input=request.user_prompt,
            quality_mode=request.quality_mode,
            client_ip=client_ip,
            resolution=request.resolution,
        )

        return GenerationResponse(
            job_id=job.job_id,
            status=job.state,
            message="Job submitted successfully. Use GET /v1/t2v/jobs/{job_id} to check status.",
        )

    except ValueError as e:
        # Validation or clarification error
        error_msg = str(e)

        # Check if clarification is required
        if "clarification" in error_msg.lower():
            # Extract clarification fields from error message
            clarification_fields = []
            # TODO: Parse clarification fields from error

            logger.warning(
                "generate_clarification_required",
                error=error_msg,
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "CLARIFICATION_REQUIRED",
                        "message": error_msg,
                    },
                    "clarification_required_fields": clarification_fields,
                }
            )
        else:
            # Regular validation error
            logger.warning(
                "generate_validation_failed",
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
            "generate_error",
            error=str(e),
            error_type=type(e).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "GENERATION_ERROR",
                    "message": "An error occurred during video generation",
                }
            }
        )
