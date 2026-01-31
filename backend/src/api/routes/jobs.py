"""
Jobs API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import re
from sqlalchemy.orm import Session

from src.models import get_db
from src.services.storage import JobDB
from src.services.observability import logger


# Response Models


class ShotAssetResponse(BaseModel):
    """Shot asset response"""

    shot_id: int
    seed: int
    video_url: str
    audio_url: str
    duration_s: int
    resolution: str


class ShotPlanShotResponse(BaseModel):
    """Simplified shot plan for frontend consumption."""

    shot_id: int
    visual_prompt: str
    narration: str
    duration: int


class ShotPlanResponse(BaseModel):
    """Shot plan wrapper used by frontend."""

    shots: List[ShotPlanShotResponse]


class JobStatusResponse(BaseModel):
    """Job status response"""

    job_id: str
    status: str
    created_at: str
    updated_at: str
    template_id: str
    quality_mode: str
    resolution: Optional[str] = None
    total_duration_s: Optional[int] = None
    shot_assets: Optional[List[ShotAssetResponse]] = None
    preview_shot_assets: Optional[List[ShotAssetResponse]] = None
    error_details: Optional[Dict[str, Any]] = None
    # Frontend compatibility fields
    script: Optional[str] = None
    shot_plan: Optional[ShotPlanResponse] = None
    assets: Optional[List[ShotAssetResponse]] = None
    error: Optional[Dict[str, Any]] = None


def _coerce_int(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        match = re.search(r"\d+", value)
        if match:
            return int(match.group(0))
    return None


def _coerce_shot_id(value: Any, fallback: int) -> int:
    coerced = _coerce_int(value)
    return coerced if coerced is not None else fallback


def _coerce_duration(value: Any) -> Optional[int]:
    return _coerce_int(value)


def _extract_narration(shot: Dict[str, Any]) -> str:
    for key in ("audio", "audio_template"):
        audio = shot.get(key)
        if isinstance(audio, dict):
            narration = audio.get("narration")
            if isinstance(narration, str):
                return narration
    narration = shot.get("narration")
    if isinstance(narration, str):
        return narration
    return ""


def _extract_visual_prompt(shot: Dict[str, Any]) -> str:
    for key in ("visual_prompt", "visual", "visual_template"):
        value = shot.get(key)
        if isinstance(value, str):
            return value
    return ""


def _build_shot_plan(shot_plan: Any) -> Optional[ShotPlanResponse]:
    if not isinstance(shot_plan, dict):
        return None
    shots = shot_plan.get("shots")
    if not isinstance(shots, list):
        return None

    simplified: List[ShotPlanShotResponse] = []
    for idx, shot in enumerate(shots):
        if not isinstance(shot, dict):
            continue
        shot_id = _coerce_shot_id(shot.get("shot_id"), idx + 1)
        visual_prompt = _extract_visual_prompt(shot)
        narration = _extract_narration(shot)
        duration = (
            _coerce_duration(shot.get("duration_s"))
            or _coerce_duration(shot.get("duration"))
            or _coerce_duration(shot.get("length_s"))
            or 0
        )
        simplified.append(
            ShotPlanShotResponse(
                shot_id=shot_id,
                visual_prompt=visual_prompt,
                narration=narration,
                duration=duration,
            )
        )

    if not simplified:
        return None
    return ShotPlanResponse(shots=simplified)


def _build_script(shot_plan: Optional[ShotPlanResponse]) -> Optional[str]:
    if shot_plan is None or not shot_plan.shots:
        return None

    lines: List[str] = []
    for shot in shot_plan.shots:
        lines.append(f"[镜头 {shot.shot_id}]")
        if shot.visual_prompt:
            lines.append(f"画面：{shot.visual_prompt}")
        if shot.narration:
            lines.append(f"旁白：{shot.narration}")
        if shot.duration:
            lines.append(f"时长：{shot.duration}s")
        lines.append("")

    return "\n".join(lines).strip()


def _normalize_shot_assets(
    shot_assets: Optional[List[Dict[str, Any]]],
    default_resolution: Optional[str],
) -> Optional[List[ShotAssetResponse]]:
    if not shot_assets:
        return None

    normalized: List[ShotAssetResponse] = []
    for idx, asset in enumerate(shot_assets):
        if not isinstance(asset, dict):
            continue
        shot_id = _coerce_shot_id(asset.get("shot_id"), idx + 1)
        seed = _coerce_int(asset.get("seed")) or 0
        duration_s = _coerce_int(asset.get("duration_s")) or 0
        resolution = asset.get("resolution") or default_resolution or ""
        normalized.append(
            ShotAssetResponse(
                shot_id=shot_id,
                seed=seed,
                video_url=str(asset.get("video_url", "")),
                audio_url=str(asset.get("audio_url", "")),
                duration_s=duration_s,
                resolution=str(resolution),
            )
        )

    return normalized or None


def _select_primary_assets(shot_assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[Any] = set()
    selected: List[Dict[str, Any]] = []
    for asset in shot_assets:
        key = asset.get("shot_id") if isinstance(asset, dict) else None
        if key in seen:
            continue
        seen.add(key)
        if isinstance(asset, dict):
            selected.append(asset)
    return selected


# Router
router = APIRouter()


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
):
    """
    Get job status and results

    Args:
        job_id: Job identifier
        db: Database session

    Returns:
        JobStatusResponse with current status and assets (if available)
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

        logger.info(
            "job_status_query",
            job_id=job_id,
            status=job.state,
        )

        # Build response
        response_data = {
            "job_id": job.job_id,
            "status": job.state,
            "created_at": job.created_at.isoformat() if job.created_at else "",
            "updated_at": job.updated_at.isoformat() if job.updated_at else "",
            "template_id": job.template_id,
            "quality_mode": job.quality_mode,
        }

        shot_plan_response = _build_shot_plan(job.shot_plan)
        if shot_plan_response:
            response_data["shot_plan"] = shot_plan_response
            script = _build_script(shot_plan_response)
            if script:
                response_data["script"] = script

        # Add output metadata if job succeeded
        if job.state == "SUCCEEDED":
            response_data["resolution"] = job.resolution
            response_data["total_duration_s"] = job.total_duration_s

            normalized_assets = _normalize_shot_assets(job.shot_assets, job.resolution)
            if normalized_assets:
                response_data["shot_assets"] = normalized_assets

                # Frontend expects a single asset per shot
                primary_assets = _select_primary_assets(job.shot_assets)
                response_data["assets"] = _normalize_shot_assets(primary_assets, job.resolution)

            normalized_previews = _normalize_shot_assets(job.preview_shot_assets, job.resolution)
            if normalized_previews:
                response_data["preview_shot_assets"] = normalized_previews

        # Add error details if job failed
        if job.state == "FAILED" and job.error_details:
            response_data["error_details"] = job.error_details
            response_data["error"] = job.error_details

        return JobStatusResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "job_status_error",
            job_id=job_id,
            error=str(e),
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An error occurred while retrieving job status",
                }
            }
        )
