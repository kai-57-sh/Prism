"""
Wan2.6 Downloader - Download generated videos from DashScope
"""

import os
import httpx
import tempfile
from typing import Optional
from pathlib import Path

from src.services.observability import logger


class Wan26Downloader:
    """
    Download generated videos from DashScope URLs
    """

    def __init__(self):
        """Initialize downloader"""
        self.client = httpx.AsyncClient(timeout=300.0)

    async def download_video(
        self,
        video_url: str,
        target_path: Optional[str] = None,
    ) -> str:
        """
        Download video from DashScope URL to local file

        Args:
            video_url: URL of video to download
            target_path: Target file path (if None, creates temp file)

        Returns:
            Path to downloaded video file

        Raises:
            httpx.HTTPError: If download fails
        """
        try:
            logger.info(
                "video_download_start",
                url=video_url,
                target_path=target_path,
            )

            # Download with streaming
            async with self.client.stream("GET", video_url) as response:
                response.raise_for_status()

                # Determine target path
                if target_path is None:
                    # Create temporary file
                    target_path = tempfile.mktemp(suffix=".mp4")

                # Ensure directory exists
                Path(target_path).parent.mkdir(parents=True, exist_ok=True)

                # Write to file
                with open(target_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)

            logger.info(
                "video_download_complete",
                url=video_url,
                target_path=target_path,
                size_bytes=os.path.getsize(target_path),
            )

            return target_path

        except Exception as e:
            logger.error(
                "video_download_failed",
                url=video_url,
                error=str(e),
            )
            raise

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
