"""
Shot Plan Models
"""

from datetime import datetime
from typing import Any, Dict, List
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, JSON, DateTime

from src.models import Base


class ShotModel(Base):
    """
    Individual Shot within a Shot Plan
    """

    __tablename__ = "shots"

    id = Column(Integer, primary_key=True, index=True)
    shot_id = Column(Integer, nullable=False)
    duration_s = Column(Integer, nullable=False)
    camera = Column(String, nullable=False)
    visual = Column(String, nullable=False)
    camera_motion = Column(String, nullable=False)
    audio = Column(JSON, nullable=False)  # {"sfx": "clock_ticking", "narration": "long term insomnia?"}
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert shot model to dictionary"""
        return {
            "shot_id": self.shot_id,
            "duration_s": self.duration_s,
            "camera": self.camera,
            "visual": self.visual,
            "camera_motion": self.camera_motion,
            "audio": self.audio,
        }


class ShotPlanModel(Base):
    """
    Shot Plan - Template instantiation result with concrete shot details
    """

    __tablename__ = "shot_plans"

    id = Column(Integer, primary_key=True, index=True)

    # Template reference
    template_id = Column(String, nullable=False)
    template_version = Column(String, nullable=False)

    # Plan details
    duration_s = Column(Integer, nullable=False)
    subtitle_policy = Column(String, nullable=False)  # "none" or "allowed"
    shots = Column(JSON, nullable=False)  # Array of ShotModel dicts
    global_style = Column(JSON, nullable=False)  # {"style": "cinematic", "lighting": "low", "color_tone": "cool", "pacing": "slow"}

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert shot plan model to dictionary"""
        return {
            "template_id": self.template_id,
            "template_version": self.template_version,
            "duration_s": self.duration_s,
            "subtitle_policy": self.subtitle_policy,
            "shots": self.shots,
            "global": self.global_style,
        }


class ShotPlan(BaseModel):
    """Pydantic shot plan model for tests."""

    template_id: str
    template_version: str
    duration_s: int
    subtitle_policy: str
    shots: List[Dict[str, Any]]
    global_style: Dict[str, Any]
