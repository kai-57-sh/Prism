"""
Shot Asset Model
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, JSON, DateTime

from src.models import Base


class ShotAssetModel(Base):
    """
    Shot Asset - Per-shot output assets (video-only and audio-only files)
    """

    __tablename__ = "shot_assets"

    id = Column(Integer, primary_key=True, index=True)

    # Shot identification
    shot_id = Column(Integer, nullable=False, index=True)
    seed = Column(Integer, nullable=False)

    # Model task reference
    model_task_id = Column(String, nullable=False)  # DashScope task ID

    # URLs
    raw_video_url = Column(String, nullable=False)  # Direct from DashScope
    video_url = Column(String, nullable=False)  # Video-only file URL
    audio_url = Column(String, nullable=False)  # Audio-only file URL

    # Storage paths
    video_path = Column(String, nullable=False)  # /var/lib/prism/static/vedios/...
    audio_path = Column(String, nullable=False)  # /var/lib/prism/static/audio/...

    # Asset metadata
    duration_s = Column(Integer, nullable=False)
    resolution = Column(String, nullable=False)  # "1280x720" or "1920x1080"

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert shot asset model to dictionary"""
        return {
            "shot_id": self.shot_id,
            "seed": self.seed,
            "model_task_id": self.model_task_id,
            "raw_video_url": self.raw_video_url,
            "video_url": self.video_url,
            "audio_url": self.audio_url,
            "video_path": self.video_path,
            "audio_path": self.audio_path,
            "duration_s": self.duration_s,
            "resolution": self.resolution,
        }


class ShotAsset(BaseModel):
    """Pydantic shot asset model for tests."""

    shot_id: int
    video_url: str
    audio_url: str
    duration_s: int
    resolution: str
    seed: Optional[int] = None
