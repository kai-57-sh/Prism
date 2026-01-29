"""
Intermediate Representation (IR) Model
"""

from datetime import datetime
from typing import Any, Dict, List
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, JSON, DateTime

from src.models import Base


class IRModel(Base):
    """
    Intermediate Representation - Structured output from LLM intent parsing

    This model is for internal use and may be embedded within Job records
    rather than stored separately in v1.
    """

    __tablename__ = "irs"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, nullable=False, index=True)
    intent = Column(String, nullable=False)
    style = Column(JSON, nullable=False)  # {"visual": "cinematic_realistic", "color_tone": "cool_dark", "lighting": "low_light"}
    scene = Column(JSON, nullable=False)  # {"location": "bedroom", "time": "midnight"}
    characters = Column(JSON, nullable=False)  # [{"type": "human", "gender": "unspecified", "age_range": "adult"}]
    emotion_curve = Column(JSON, nullable=False)  # ["anxiety", "tired", "slight_relief"]
    subtitle_policy = Column(String, nullable=False)  # "none" or "allowed"
    audio = Column(JSON, nullable=False)  # {"mode": "auto_voiceover_in_prompt", "narration_language": "zh-CN", ...}
    duration_preference_s = Column(Integer, nullable=False)
    quality_mode = Column(String, nullable=False)  # "fast", "balanced", "high"
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert IR model to dictionary"""
        return {
            "topic": self.topic,
            "intent": self.intent,
            "style": self.style,
            "scene": self.scene,
            "characters": self.characters,
            "emotion_curve": self.emotion_curve,
            "subtitle_policy": self.subtitle_policy,
            "audio": self.audio,
            "duration_preference_s": self.duration_preference_s,
            "quality_mode": self.quality_mode,
        }


class IR(BaseModel):
    """Pydantic IR model for tests and lightweight usage."""

    topic: str
    intent: str
    style: Dict[str, Any]
    scene: Dict[str, Any]
    characters: List[Dict[str, Any]]
    emotion_curve: List[str]
    subtitle_policy: str
    audio: Dict[str, Any]
    duration_preference_s: int
    quality_mode: str
