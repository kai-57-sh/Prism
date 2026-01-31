"""
Wan2.6-t2v Adapter - DashScope text-to-video API integration
"""

import asyncio
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
try:
    from dashscope import VideoSynthesis
except Exception:  # pragma: no cover - optional dependency for tests
    VideoSynthesis = None
from http import HTTPStatus

from src.config.settings import settings
from src.services.observability import logger


class ShotGenerationRequest(BaseModel):
    """Request for single shot generation"""

    prompt: str
    negative_prompt: str = ""
    size: str = "1280*720"  # "1280*720" or "1920*1080"
    duration: int = 5  # Seconds
    seed: int = 12345
    prompt_extend: bool = False
    watermark: bool = False


class ShotGenerationResponse(BaseModel):
    """Response from shot generation"""

    task_id: str
    status: str
    video_url: Optional[str] = None
    error: Optional[str] = None


class Wan26Adapter:
    """
    Adapter for DashScope wan2.6-t2v text-to-video API
    Uses DashScope VideoSynthesis SDK
    """

    def __init__(self):
        """Initialize wan2.6 adapter"""
        self.api_key = settings.dashscope_api_key

    def _format_task_error(
        self,
        task_status: str,
        rsp: Any,
        output_payload: Optional[Dict[str, Any]],
    ) -> str:
        parts: List[str] = []
        if task_status:
            parts.append(f"task_status={task_status}")

        code = getattr(rsp, "code", None)
        message = getattr(rsp, "message", None)
        if code:
            parts.append(f"code={code}")
        if message:
            parts.append(f"message={message}")

        if output_payload:
            for key in ("code", "message", "error", "error_code", "error_msg", "reason", "failed_reason"):
                value = output_payload.get(key)
                if value:
                    parts.append(f"{key}={value}")

        return "; ".join(parts) if parts else "Video synthesis failed without error details"

    async def submit_shot_request(
        self,
        request: ShotGenerationRequest,
    ) -> ShotGenerationResponse:
        """
        Submit single shot generation request to DashScope

        Args:
            request: Shot generation request

        Returns:
            ShotGenerationResponse with task_id

        Raises:
            Exception: If API request fails
        """
        try:
            logger.info(
                "submit_shot_request",
                prompt_length=len(request.prompt),
                size=request.size,
                duration=request.duration,
                seed=request.seed,
            )

            if VideoSynthesis is None:
                raise ImportError("dashscope VideoSynthesis is not available")

            # Use DashScope VideoSynthesis async_call
            rsp = await asyncio.to_thread(
                VideoSynthesis.async_call,
                api_key=self.api_key,
                model='wan2.6-t2v',
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                size=request.size,
                duration=request.duration,
                seed=request.seed,
                prompt_extend=request.prompt_extend,
                watermark=request.watermark,
            )

            if rsp.status_code == HTTPStatus.OK:
                task_id = rsp.output.task_id
                logger.info(
                    "shot_request_submitted",
                    task_id=task_id,
                )

                return ShotGenerationResponse(
                    task_id=task_id,
                    status="submitted",
                )
            else:
                error_msg = f'Failed, status_code: {rsp.status_code}, code: {rsp.code}, message: {rsp.message}'
                logger.error(
                    "shot_request_failed",
                    error=error_msg,
                )
                raise Exception(error_msg)

        except Exception as e:
            logger.error(
                "shot_request_failed",
                error=str(e),
            )
            raise

    async def poll_task_status(
        self,
        task_id: str,
        max_attempts: int = 60,
        poll_interval: int = 5,
    ) -> ShotGenerationResponse:
        """
        Poll task status until completion or timeout using DashScope wait()

        Args:
            task_id: DashScope task ID
            max_attempts: Maximum number of polling attempts (not used with wait())
            poll_interval: Seconds between polls (not used with wait())

        Returns:
            ShotGenerationResponse with status and video_url if successful

        Raises:
            Exception: If task fails or times out
        """
        try:
            if VideoSynthesis is None:
                raise ImportError("dashscope VideoSynthesis is not available")

            # Use DashScope VideoSynthesis.wait() for automatic polling
            logger.info(
                "task_wait_start",
                task_id=task_id,
            )

            rsp = await asyncio.to_thread(
                VideoSynthesis.wait,
                task=task_id,
                api_key=self.api_key,
            )

            if rsp.status_code == HTTPStatus.OK:
                output_payload: Dict[str, Any] = (
                    rsp.output if isinstance(rsp.output, dict) else {}
                )
                raw_task_status = None
                raw_video_url = None
                if rsp.output is not None:
                    if isinstance(rsp.output, dict):
                        raw_task_status = rsp.output.get("task_status")
                        raw_video_url = rsp.output.get("video_url")
                    else:
                        raw_task_status = getattr(rsp.output, "task_status", None)
                        raw_video_url = getattr(rsp.output, "video_url", None)

                task_status = raw_task_status if isinstance(raw_task_status, str) else ""
                video_url = raw_video_url if isinstance(raw_video_url, str) else ""
                normalized_status = task_status.strip().lower()

                if normalized_status and normalized_status not in {
                    "succeeded",
                    "success",
                    "completed",
                    "done",
                    "finished",
                }:
                    error_msg = self._format_task_error(task_status, rsp, output_payload)
                    logger.error(
                        "task_failed",
                        task_id=task_id,
                        task_status=task_status,
                        error=error_msg,
                    )
                    return ShotGenerationResponse(
                        task_id=task_id,
                        status="failed",
                        error=error_msg,
                    )

                if not video_url:
                    error_msg = self._format_task_error(task_status, rsp, output_payload)
                    if not error_msg:
                        error_msg = "Video synthesis completed but no video_url returned"
                    logger.error(
                        "task_failed",
                        task_id=task_id,
                        task_status=task_status or "unknown",
                        error=error_msg,
                    )
                    return ShotGenerationResponse(
                        task_id=task_id,
                        status="failed",
                        error=error_msg,
                    )

                logger.info(
                    "task_completed",
                    task_id=task_id,
                    task_status=task_status or "unknown",
                    video_url=video_url,
                )

                return ShotGenerationResponse(
                    task_id=task_id,
                    status="succeeded",
                    video_url=video_url,
                )
            else:
                error_msg = f'Failed, status_code: {rsp.status_code}, code: {rsp.code}, message: {rsp.message}'
                logger.error(
                    "task_failed",
                    task_id=task_id,
                    error=error_msg,
                )

                return ShotGenerationResponse(
                    task_id=task_id,
                    status="failed",
                    error=error_msg,
                )

        except Exception as e:
            logger.error(
                "task_poll_error",
                task_id=task_id,
                error=str(e),
            )
            raise

    async def close(self):
        """Close resources (no-op for DashScope SDK)"""
        pass


class Wan26RetryAdapter(Wan26Adapter):
    """
    Wan2.6 adapter with automatic retry logic for retryable errors
    """

    MAX_RETRY_ATTEMPTS = 3
    RETRY_INITIAL_DELAY_S = 2
    RETRY_MAX_DELAY_S = 20

    async def submit_shot_request_with_retry(
        self,
        request: ShotGenerationRequest,
    ) -> ShotGenerationResponse:
        """
        Submit shot request with retry logic for retryable errors

        Args:
            request: Shot generation request

        Returns:
            ShotGenerationResponse

        Raises:
            Exception: If all retry attempts exhausted
        """
        last_error = None

        for attempt in range(self.MAX_RETRY_ATTEMPTS):
            try:
                return await self.submit_shot_request(request)
            except Exception as e:
                last_error = e
                error_type = type(e).__name__

                logger.warning(
                    "shot_request_retry",
                    attempt=attempt + 1,
                    max_attempts=self.MAX_RETRY_ATTEMPTS,
                    error_type=error_type,
                    error=str(e),
                )

                # Check if error is retryable
                if self._is_retryable_error(e):
                    # Exponential backoff using asyncio
                    delay = min(
                        self.RETRY_INITIAL_DELAY_S * (2 ** attempt),
                        self.RETRY_MAX_DELAY_S,
                    )
                    await asyncio.sleep(delay)
                else:
                    # Non-retryable error, raise immediately
                    raise

        # All retries exhausted
        logger.error(
            "shot_request_exhausted",
            max_attempts=self.MAX_RETRY_ATTEMPTS,
            last_error=str(last_error),
        )
        raise last_error

    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Determine if error is retryable

        Args:
            error: Exception to check

        Returns:
            True if error is retryable
        """
        # Network errors and timeout errors are retryable
        error_message = str(error).lower()
        retryable_keywords = [
            'timeout',
            'connection',
            'network',
            'temporary',
            '500',
            '502',
            '503',
            '504',
        ]

        return any(keyword in error_message for keyword in retryable_keywords)
