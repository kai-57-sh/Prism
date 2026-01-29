"""
Template Model
"""

from sqlalchemy import Column, Integer, String, JSON, DateTime, UniqueConstraint
from datetime import datetime

from src.models import Base


class TemplateModel(Base):
    """
    Medical Scene Template - Reusable storyboard asset defining shot structure, style, and constraints
    """

    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)

    # Business identifiers
    template_id = Column(String, nullable=False, unique=True, index=True)
    version = Column(String, nullable=False)

    # Template metadata
    tags = Column(JSON, nullable=False)  # {"topic": ["insomnia"], "tone": ["anxious"], "style": ["cinematic"], "subtitle_policy": "none"}
    constraints = Column(JSON, nullable=False)  # {"duration_s_range": [2, 15], "allowed_sizes": ["1280*720", "1920*1080"], "fps": 30, "watermark_default": false}
    shot_skeletons = Column(JSON, nullable=False)  # Array of shot templates with placeholders
    negative_prompt_base = Column(String, nullable=False, default="")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint on template_id and version
    __table_args__ = (
        UniqueConstraint("template_id", "version", name="uq_template_version"),
    )

    def to_dict(self) -> dict:
        """Convert template model to dictionary"""
        return {
            "id": self.id,
            "template_id": self.template_id,
            "version": self.version,
            "tags": self.tags,
            "constraints": self.constraints,
            "shot_skeletons": self.shot_skeletons,
            "negative_prompt_base": self.negative_prompt_base,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
