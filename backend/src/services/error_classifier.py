"""
Error Classifier - Classify errors as retryable or non-retryable
"""

from typing import Dict, Any
import httpx


class ErrorClassifier:
    """
    Classify errors for retry logic and user-facing messages
    """

    # Error codes
    ERROR_NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    ERROR_NETWORK_ERROR = "NETWORK_ERROR"
    ERROR_DASHSCOPE_TIMEOUT = "DASHSCOPE_TIMEOUT"
    ERROR_DASHSCOPE_RATE_LIMIT = "DASHSCOPE_RATE_LIMIT"
    ERROR_DASHSCOPE_AUTH = "DASHSCOPE_AUTH"
    ERROR_DASHSCOPE_CONTENT_VIOLATION = "DASHSCOPE_CONTENT_VIOLATION"
    ERROR_DASHSCOPE_INVALID_PARAM = "DASHSCOPE_INVALID_PARAM"
    ERROR_FFMPEG_NOT_FOUND = "FFMPEG_NOT_FOUND"
    ERROR_FFMPEG_EXTRACTION_FAILED = "FFMPEG_EXTRACTION_FAILED"
    ERROR_FFMPEG_AUDIO_MISSING = "FFMPEG_AUDIO_MISSING"
    ERROR_VALIDATION_FAILED = "VALIDATION_FAILED"
    ERROR_TEMPLATE_NOT_FOUND = "TEMPLATE_NOT_FOUND"
    ERROR_JOB_TIMEOUT = "JOB_TIMEOUT"
    ERROR_UNKNOWN = "UNKNOWN_ERROR"

    def classify(self, error: Exception) -> Dict[str, Any]:
        """
        Classify error with user-facing message

        Args:
            error: Exception to classify

        Returns:
            Dict with code, message, classification, retryable, suggested_modifications
        """
        if isinstance(error, httpx.TimeoutException):
            return {
                "code": self.ERROR_NETWORK_TIMEOUT,
                "message": "Network timeout while connecting to video generation service",
                "classification": "retryable",
                "retryable": True,
                "suggested_modifications": [],
            }

        elif isinstance(error, httpx.NetworkError):
            return {
                "code": self.ERROR_NETWORK_ERROR,
                "message": "Network error occurred",
                "classification": "retryable",
                "retryable": True,
                "suggested_modifications": [],
            }

        elif isinstance(error, httpx.HTTPStatusError):
            status = error.response.status_code

            if status == 401:
                return {
                    "code": self.ERROR_DASHSCOPE_AUTH,
                    "message": "Authentication failed. Please check API credentials",
                    "classification": "non_retryable",
                    "retryable": False,
                    "suggested_modifications": ["Verify DASHSCOPE_API_KEY is correct"],
                }

            elif status == 429:
                return {
                    "code": self.ERROR_DASHSCOPE_RATE_LIMIT,
                    "message": "Rate limit exceeded for video generation service",
                    "classification": "retryable",
                    "retryable": True,
                    "suggested_modifications": ["Wait a few minutes and try again"],
                }

            elif 400 <= status < 500:
                # Client error - non-retryable
                return {
                    "code": self.ERROR_DASHSCOPE_INVALID_PARAM,
                    "message": f"Invalid request parameters: {error.response.text}",
                    "classification": "non_retryable",
                    "retryable": False,
                    "suggested_modifications": ["Check request parameters and try again"],
                }

            elif 500 <= status < 600:
                # Server error - retryable
                return {
                    "code": self.ERROR_DASHSCOPE_TIMEOUT,
                    "message": "Video generation service temporarily unavailable",
                    "classification": "retryable",
                    "retryable": True,
                    "suggested_modifications": ["Try again in a few minutes"],
                }

        # FFmpeg errors
        if "FFmpegError" in type(error).__name__:
            from src.services.ffmpeg_splitter import FFmpegError
            if isinstance(error, FFmpegError):
                return {
                    "code": error.code,
                    "message": error.message,
                    "classification": "non_retryable",
                    "retryable": False,
                    "suggested_modifications": self._get_ffmpeg_suggestions(error.code),
                }

        # Validation errors
        if "ValidationError" in type(error).__name__ or "ValueError" in type(error).__name__:
            return {
                "code": self.ERROR_VALIDATION_FAILED,
                "message": str(error),
                "classification": "non_retryable",
                "retryable": False,
                "suggested_modifications": self._extract_validation_suggestions(error),
            }

        # Default - unknown error
        return {
            "code": self.ERROR_UNKNOWN,
            "message": f"An unexpected error occurred: {str(error)}",
            "classification": "non_retryable",
            "retryable": False,
            "suggested_modifications": ["Please try again or contact support"],
        }

    def _get_ffmpeg_suggestions(self, error_code: str) -> list:
        """
        Get user-facing suggestions for FFmpeg errors

        Args:
            error_code: FFmpeg error code

        Returns:
            List of suggestion strings
        """
        suggestions_map = {
            "FFMPEG_NOT_FOUND": [
                "FFmpeg is not installed on the server",
                "Contact system administrator",
            ],
            "INPUT_FILE_NOT_FOUND": [
                "Generated video file not found",
                "Try regenerating the video",
            ],
            "EXTRACTION_FAILED": [
                "Video processing failed",
                "The video may be corrupted",
                "Try regenerating with different parameters",
            ],
            "AUDIO_STREAM_MISSING": [
                "The generated video has no audio track",
                "Try regenerating with audio enabled",
            ],
        }

        return suggestions_map.get(error_code, ["Video processing error"])

    def _extract_validation_suggestions(self, error: Exception) -> list:
        """
        Extract suggestions from validation error

        Args:
            error: Validation error

        Returns:
            List of suggestion strings
        """
        suggestions = []

        # Check if error has suggested_modifications attribute
        if hasattr(error, "suggested_modifications"):
            suggestions.extend(error.suggested_modifications)

        # Check error message for common patterns
        error_msg = str(error).lower()

        if "duration" in error_msg:
            suggestions.append("Adjust video duration to be between 2-15 seconds")

        if "resolution" in error_msg:
            suggestions.append("Use supported resolution: 1280x720 or 1920x1080")

        if "subtitle" in error_msg:
            suggestions.append("Review subtitle policy requirements")

        return suggestions
