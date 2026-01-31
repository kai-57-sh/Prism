"""
Shot Request Model
"""

from datetime import datetime
from typing import Any, Dict
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, JSON, DateTime, Float

from src.models import Base


class ShotRequestModel(Base):
    """
    Shot Request - Per-shot compiled prompt and generation parameters
    """

    __tablename__ = "shot_requests"

    id = Column(Integer, primary_key=True, index=True)

    # Shot identification
    shot_id = Column(Integer, nullable=False, index=True)

    # Compiled prompts
    compiled_prompt = Column(String, nullable=False)
    compiled_negative_prompt = Column(String, nullable=False)

    # Generation parameters
    params = Column(JSON, nullable=False)  # {"model": "wan2.6-t2v", "size": "1280*720", "duration": 4, "seed": 12345, "prompt_extend": false, "watermark": false}

    # Prompt extension flag
    prompt_extend = Column(JSON, nullable=False)  # Stores prompt_extend configuration

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert shot request model to dictionary"""
        return {
            "shot_id": self.shot_id,
            "compiled_prompt": self.compiled_prompt,
            "compiled_negative_prompt": self.compiled_negative_prompt,
            "params": self.params,
        }


class ShotRequest(BaseModel):
    """Pydantic shot request model for tests."""

    shot_id: int
    compiled_prompt: str
    compiled_negative_prompt: str
    params: Dict[str, Any]
