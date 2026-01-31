"""
Template Base - Template loading, validation, and instantiation
"""

import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from pydantic import BaseModel, Field, validator

from src.config.settings import settings


class ShotSkeleton(BaseModel):
    """Individual shot template with placeholders"""

    shot_id: int
    duration_s: int
    camera: str
    visual_template: str
    audio_template: Dict[str, str]
    subtitle_policy: str = Field(..., regex=r"^(none|allowed|auto)$")

    @validator("duration_s")
    def validate_duration(cls, v):
        if v < 2 or v > 15:
            raise ValueError("Shot duration must be between 2 and 15 seconds")
        return v


class TemplateConstraints(BaseModel):
    """Template constraints"""

    duration_s_range: List[int]  # [min, max]
    allowed_sizes: List[str]  # ["1280*720", "1920*1080"]
    fps: int = 30
    watermark_default: bool = False

    @validator("duration_s_range")
    def validate_duration_range(cls, v):
        if v[0] < 2 or v[1] > 15:
            raise ValueError("Duration must be between 2 and 15 seconds")
        if v[0] > v[1]:
            raise ValueError("Min duration cannot exceed max duration")
        return v


class TemplateTags(BaseModel):
    """Template tags for semantic search"""

    topic: List[str]
    tone: List[str]
    style: List[str]
    subtitle_policy: str = Field(..., regex=r"^(none|allowed|auto)$")


class Template(BaseModel):
    """Medical scene template"""

    template_id: str = Field(..., regex=r"^[a-z_]+$")
    version: str = Field(..., regex=r"^\d+\.\d+\.\d+$")
    tags: TemplateTags
    constraints: TemplateConstraints
    shot_skeletons: List[ShotSkeleton]
    negative_prompt_base: str

    @validator("shot_skeletons")
    def validate_shot_skeletons(cls, v):
        if len(v) == 0:
            raise ValueError("Shot skeletons cannot be empty")
        return v

    @validator("negative_prompt_base")
    def validate_negative_prompt(cls, v):
        if not v or not v.strip():
            raise ValueError("Negative prompt base cannot be empty")
        return v


class TemplateLoader:
    """
    Load and validate medical scene templates from JSON files
    """

    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize template loader

        Args:
            template_dir: Directory containing template JSON files
        """
        if template_dir is None:
            template_dir = os.path.join(
                os.path.dirname(__file__),
                "medical_scenes"
            )

        self.template_dir = template_dir
        self._templates: Dict[str, Template] = {}

    def load_template(self, template_id: str, version: str = "1.0.0") -> Optional[Template]:
        """
        Load a single template from file

        Args:
            template_id: Template identifier
            version: Template version

        Returns:
            Template object or None if not found
        """
        filename = f"{template_id}_v{version.replace('.', '_')}.json"
        filepath = os.path.join(self.template_dir, filename)

        if not os.path.exists(filepath):
            return None

        with open(filepath, "r") as f:
            data = json.load(f)

        return Template(**data)

    def load_all_templates(self) -> Dict[str, Template]:
        """
        Load all templates from directory

        Returns:
            Dictionary mapping template_id to Template objects
        """
        templates = {}

        if not os.path.exists(self.template_dir):
            return templates

        for filename in os.listdir(self.template_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.template_dir, filename)

                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)

                    template = Template(**data)
                    key = f"{template.template_id}:{template.version}"
                    templates[key] = template
                except Exception as e:
                    # Log error but continue loading other templates
                    print(f"Error loading template {filename}: {e}")

        return templates

    def validate_template(self, template_data: Dict[str, Any]) -> Template:
        """
        Validate template data and return Template object

        Args:
            template_data: Template dictionary

        Returns:
            Validated Template object

        Raises:
            ValidationError: If template data is invalid
        """
        return Template(**template_data)

    def instantiate_template(
        self,
        template: Template,
        shot_values: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Instantiate template with concrete values

        Args:
            template: Template object
            shot_values: List of dictionaries with values for template placeholders

        Returns:
            List of instantiated shot dictionaries
        """
        instantiated_shots = []

        for shot_skeleton, values in zip(template.shot_skeletons, shot_values):
            # Instantiate visual template
            visual = shot_skeleton.visual_template.format(**values)

            # Instantiate shot
            shot = {
                "shot_id": shot_skeleton.shot_id,
                "duration_s": shot_skeleton.duration_s,
                "camera": shot_skeleton.camera,
                "visual": visual,
                "camera_motion": values.get("camera_motion", "static"),
                "audio": {
                    "sfx": shot_skeleton.audio_template.get("sfx", ""),
                    "narration": values.get("narration", ""),
                },
                "subtitle_policy": shot_skeleton.subtitle_policy,
            }

            instantiated_shots.append(shot)

        return instantiated_shots
