"""
Asset Storage Service - Manages video, audio, and metadata file paths
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.config.settings import settings


class AssetStorage:
    """
    Manages storage paths and URLs for video, audio, and metadata files
    """

    def __init__(self):
        """Initialize asset storage"""
        self.static_root = settings.static_root
        self.video_dir = settings.static_video_dir
        self.audio_dir = settings.static_audio_dir
        self.metadata_dir = settings.static_metadata_dir
        self.static_url_prefix = settings.static_url_prefix
        self.video_subdir = settings.static_video_subdir
        self.audio_subdir = settings.static_audio_subdir
        self.metadata_subdir = settings.static_metadata_subdir

        # Ensure directories exist
        self._ensure_directories()

    def _ensure_directories(self):
        """Create storage directories if they don't exist"""
        for directory in [self.video_dir, self.audio_dir, self.metadata_dir]:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def get_video_storage_path(
        self,
        job_id: str,
        shot_id: int,
        extension: str = "mp4",
        suffix: Optional[str] = None,
    ) -> str:
        """
        Get storage path for video file

        Args:
            job_id: Job identifier
            shot_id: Shot identifier
            extension: File extension (default: mp4)

        Returns:
            Absolute file path for video storage
        """
        date_str = datetime.utcnow().strftime("%Y/%m/%d")
        base = f"{job_id}_shot_{shot_id}"
        if suffix:
            base = f"{base}_{suffix}"
        filename = f"{base}.{extension}"
        path = os.path.join(self.video_dir, date_str, filename)

        # Ensure date directory exists
        Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)

        return path

    def get_audio_storage_path(
        self,
        job_id: str,
        shot_id: int,
        extension: str = "mp3",
        suffix: Optional[str] = None,
    ) -> str:
        """
        Get storage path for audio file

        Args:
            job_id: Job identifier
            shot_id: Shot identifier
            extension: File extension (default: mp3)

        Returns:
            Absolute file path for audio storage
        """
        date_str = datetime.utcnow().strftime("%Y/%m/%d")
        base = f"{job_id}_shot_{shot_id}"
        if suffix:
            base = f"{base}_{suffix}"
        filename = f"{base}.{extension}"
        path = os.path.join(self.audio_dir, date_str, filename)

        # Ensure date directory exists
        Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)

        return path

    def get_metadata_storage_path(self, job_id: str) -> str:
        """
        Get storage path for metadata JSON file

        Args:
            job_id: Job identifier

        Returns:
            Absolute file path for metadata storage
        """
        filename = f"{job_id}.json"
        path = os.path.join(self.metadata_dir, filename)
        return path

    def get_video_url(
        self,
        job_id: str,
        shot_id: int,
        extension: str = "mp4",
        suffix: Optional[str] = None,
    ) -> str:
        """
        Get URL for video file

        Args:
            job_id: Job identifier
            shot_id: Shot identifier
            extension: File extension (default: mp4)

        Returns:
            URL path for video file
        """
        date_str = datetime.utcnow().strftime("%Y/%m/%d")
        base = f"{job_id}_shot_{shot_id}"
        if suffix:
            base = f"{base}_{suffix}"
        filename = f"{base}.{extension}"
        return f"{self.static_url_prefix}/{self.video_subdir}/{date_str}/{filename}"

    def get_audio_url(
        self,
        job_id: str,
        shot_id: int,
        extension: str = "mp3",
        suffix: Optional[str] = None,
    ) -> str:
        """
        Get URL for audio file

        Args:
            job_id: Job identifier
            shot_id: Shot identifier
            extension: File extension (default: mp3)

        Returns:
            URL path for audio file
        """
        date_str = datetime.utcnow().strftime("%Y/%m/%d")
        base = f"{job_id}_shot_{shot_id}"
        if suffix:
            base = f"{base}_{suffix}"
        filename = f"{base}.{extension}"
        return f"{self.static_url_prefix}/{self.audio_subdir}/{date_str}/{filename}"

    def get_metadata_url(self, job_id: str) -> str:
        """
        Get URL for metadata file

        Args:
            job_id: Job identifier

        Returns:
            URL path for metadata file
        """
        filename = f"{job_id}.json"
        return f"{self.static_url_prefix}/{self.metadata_subdir}/{filename}"

    def write_job_metadata(
        self,
        job_id: str,
        metadata: Dict[str, Any],
    ) -> str:
        """
        Write job metadata to JSON file

        Args:
            job_id: Job identifier
            metadata: Job metadata dictionary

        Returns:
            File path where metadata was written
        """
        path = self.get_metadata_storage_path(job_id)

        with open(path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

        return path

    def read_job_metadata(self, job_id: str) -> Dict[str, Any]:
        """
        Read job metadata from JSON file

        Args:
            job_id: Job identifier

        Returns:
            Job metadata dictionary
        """
        path = self.get_metadata_storage_path(job_id)

        if not os.path.exists(path):
            raise FileNotFoundError(f"Metadata file not found: {path}")

        with open(path, "r") as f:
            return json.load(f)

    def delete_job_assets(self, job_id: str) -> List[str]:
        """
        Delete all assets for a job

        Args:
            job_id: Job identifier

        Returns:
            List of deleted file paths
        """
        deleted_paths = []

        # Delete video files
        date_str = datetime.utcnow().strftime("%Y/%m/%d")
        video_pattern = f"{job_id}_shot_"
        video_dir = os.path.join(self.video_dir, date_str)

        if os.path.exists(video_dir):
            for filename in os.listdir(video_dir):
                if filename.startswith(video_pattern) and filename.endswith(".mp4"):
                    path = os.path.join(video_dir, filename)
                    os.remove(path)
                    deleted_paths.append(path)

        # Delete audio files
        audio_dir = os.path.join(self.audio_dir, date_str)
        if os.path.exists(audio_dir):
            for filename in os.listdir(audio_dir):
                if filename.startswith(video_pattern) and filename.endswith(".mp3"):
                    path = os.path.join(audio_dir, filename)
                    os.remove(path)
                    deleted_paths.append(path)

        # Delete metadata file
        metadata_path = self.get_metadata_storage_path(job_id)
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
            deleted_paths.append(metadata_path)

        return deleted_paths
