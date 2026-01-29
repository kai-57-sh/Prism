"""
FFmpeg Splitter - Split video into video-only and audio-only files
"""

import subprocess
import shutil
import os
import tempfile
from typing import Tuple, Optional, Dict, Any
from pathlib import Path

from src.config.settings import settings
from src.config.constants import (
    FFMPEG_VIDEO_CODEC,
    FFMPEG_AUDIO_CODEC,
    FFMPEG_VIDEO_BITRATE,
    FFMPEG_AUDIO_BITRATE,
)
from src.services.observability import logger


class FFmpegError(Exception):
    """FFmpeg processing error"""

    def __init__(self, message: str, code: str, details: Optional[str] = None):
        self.message = message
        self.code = code
        self.details = details
        super().__init__(self.message)


class FFmpegSplitter:
    """
    Split video files into video-only and audio-only components using ffmpeg
    """

    # Error codes
    ERROR_FFMPEG_NOT_FOUND = "FFMPEG_NOT_FOUND"
    ERROR_INPUT_FILE_NOT_FOUND = "INPUT_FILE_NOT_FOUND"
    ERROR_EXTRACTION_FAILED = "EXTRACTION_FAILED"
    ERROR_AUDIO_STREAM_MISSING = "AUDIO_STREAM_MISSING"

    def __init__(self):
        """Initialize FFmpeg splitter"""
        self.ffmpeg_path = settings.ffmpeg_path
        self.video_codec = FFMPEG_VIDEO_CODEC  # libx264
        self.audio_codec = FFMPEG_AUDIO_CODEC  # mp3
        self.video_bitrate = FFMPEG_VIDEO_BITRATE  # 2M
        self.audio_bitrate = FFMPEG_AUDIO_BITRATE  # 192k

    def split_video_audio(
        self,
        input_path: str,
        video_output_path: str,
        audio_output_path: str,
    ) -> Dict[str, Any]:
        """
        Split video file into video-only and audio-only files

        Args:
            input_path: Path to input video file
            video_output_path: Path for video-only output
            audio_output_path: Path for audio-only output

        Returns:
            Dict with success status, durations, and file sizes

        Raises:
            FFmpegError: If splitting fails
        """
        # Validate input file exists
        if not os.path.exists(input_path):
            raise FFmpegError(
                f"Input file not found: {input_path}",
                self.ERROR_INPUT_FILE_NOT_FOUND,
            )

        if not self._is_ffmpeg_available():
            raise FFmpegError(
                f"FFmpeg not found: {self.ffmpeg_path}",
                self.ERROR_FFMPEG_NOT_FOUND,
            )

        # Ensure output directories exist
        Path(video_output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(audio_output_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            # Extract video-only stream
            logger.info(
                "video_extraction_start",
                input_path=input_path,
                output_path=video_output_path,
            )

            video_result = self._extract_video(
                input_path,
                video_output_path,
            )

            if video_result.returncode != 0:
                error_msg = video_result.stderr.decode('utf-8', errors='ignore')
                raise FFmpegError(
                    f"Video extraction failed: {error_msg}",
                    self.ERROR_EXTRACTION_FAILED,
                    details=error_msg,
                )

            # Extract audio-only stream
            logger.info(
                "audio_extraction_start",
                input_path=input_path,
                output_path=audio_output_path,
            )

            audio_result = self._extract_audio(
                input_path,
                audio_output_path,
            )

            if audio_result.returncode != 0:
                error_msg = audio_result.stderr.decode('utf-8', errors='ignore')
                raise FFmpegError(
                    f"Audio extraction failed: {error_msg}",
                    self.ERROR_EXTRACTION_FAILED,
                    details=error_msg,
                )

            # Get file info
            video_duration = self._get_video_duration(video_output_path)
            video_size = os.path.getsize(video_output_path)
            audio_size = os.path.getsize(audio_output_path)

            logger.info(
                "ffmpeg_split_complete",
                video_path=video_output_path,
                audio_path=audio_output_path,
                duration_s=video_duration,
                video_size_bytes=video_size,
                audio_size_bytes=audio_size,
            )

            return {
                "success": True,
                "video_path": video_output_path,
                "audio_path": audio_output_path,
                "duration_s": video_duration,
                "video_size_bytes": video_size,
                "audio_size_bytes": audio_size,
            }

        except FFmpegError:
            raise
        except Exception as e:
            logger.error(
                "ffmpeg_split_error",
                input_path=input_path,
                error=str(e),
            )
            raise FFmpegError(
                f"FFmpeg processing failed: {str(e)}",
                self.ERROR_EXTRACTION_FAILED,
                details=str(e),
            )

    def _is_ffmpeg_available(self) -> bool:
        if os.path.isabs(self.ffmpeg_path) or os.sep in self.ffmpeg_path:
            return os.path.exists(self.ffmpeg_path) and os.access(self.ffmpeg_path, os.X_OK)
        return shutil.which(self.ffmpeg_path) is not None

    def _extract_video(
        self,
        input_path: str,
        output_path: str,
    ) -> subprocess.CompletedProcess:
        """
        Extract video-only stream (no audio)

        Args:
            input_path: Input video file path
            output_path: Output video file path

        Returns:
            subprocess result
        """
        cmd = [
            self.ffmpeg_path,
            "-i", input_path,
            "-c:v", self.video_codec,
            "-b:v", self.video_bitrate,
            "-an",  # No audio
            "-y",  # Overwrite output file
            output_path,
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        return result

    def _extract_audio(
        self,
        input_path: str,
        output_path: str,
    ) -> subprocess.CompletedProcess:
        """
        Extract audio-only stream (no video)

        Args:
            input_path: Input video file path
            output_path: Output audio file path

        Returns:
            subprocess result
        """
        cmd = [
            self.ffmpeg_path,
            "-i", input_path,
            "-vn",  # No video
            "-c:a", self.audio_codec,
            "-b:a", self.audio_bitrate,
            "-y",  # Overwrite output file
            output_path,
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        return result

    def _get_video_duration(self, video_path: str) -> float:
        """
        Get video duration in seconds using ffprobe

        Args:
            video_path: Path to video file

        Returns:
            Duration in seconds
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
            else:
                # Fallback: assume 5 seconds
                return 5.0

        except Exception as e:
            logger.warning(
                "ffprobe_duration_failed",
                video_path=video_path,
                error=str(e),
            )
            # Fallback: assume 5 seconds
            return 5.0

    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        Get video metadata using ffprobe

        Args:
            video_path: Path to video file

        Returns:
            Dict with video metadata
        """
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if result.returncode == 0:
                import json
                metadata = json.loads(result.stdout)
                return metadata
            else:
                return {}

        except Exception as e:
            logger.error(
                "ffprobe_info_failed",
                video_path=video_path,
                error=str(e),
            )
            return {}
