"""
Prompt Compiler - Jinja2-based per-shot prompt compilation
"""

from typing import Dict, Any, List, Optional, Tuple
from jinja2 import Template, Environment, BaseLoader
from pydantic import BaseModel

from src.config.constants import FFMPEG_VIDEO_CODEC, FFMPEG_AUDIO_CODEC


class CompiledPrompt(BaseModel):
    """Compiled prompt with all sections"""

    compiled_prompt: str
    compiled_negative_prompt: str
    params: Dict[str, Any]


class PromptCompiler:
    """
    Compile per-shot prompts using Jinja2 templates with fixed 4-section schema
    """

    # Fixed section templates
    GLOBAL_REQUIREMENTS_TEMPLATE = """全片要求：{{ visual_style }}、{{ lighting }}、{{ color_tone }}、{{ scene_desc }}、{{ emotion_desc }}{% if subtitle_policy == 'none' %}、无字幕无文字无水印无logo{% endif %}"""

    SHOT_SCRIPT_TEMPLATE = """镜头脚本：[{{ start_time }}-{{ end_time }}s] {{ shot_description }}"""

    AUDIO_TEMPLATE = """音频：环境音（{{ sfx }}）；旁白（{{ narration_language }}、{{ narration_tone }}）："{{ narration }}" """

    CONSISTENCY_TEMPLATE = """一致性：{{ consistency_notes }}"""

    def __init__(self):
        """Initialize prompt compiler"""
        self.jinja_env = Environment(loader=BaseLoader())

    def compile_shot_prompt(
        self,
        shot: Dict[str, Any],
        shot_plan: Optional[Dict[str, Any]] = None,
        ir: Optional[Dict[str, Any]] = None,
        negative_prompt_base: str = "",
        prompt_extend: bool = False,
        quality_mode: str = "balanced",
    ):
        """
        Compile a single shot prompt with fixed 4-section schema

        Args:
            shot: Shot dictionary with shot_id, duration_s, camera, visual, camera_motion, audio
            shot_plan: Full shot plan with global settings
            ir: Intermediate Representation
            negative_prompt_base: Base negative prompt from template
            prompt_extend: Whether to enable prompt extension
            quality_mode: Quality mode

        Returns:
            CompiledPrompt object
        """
        if ir is None and (shot_plan is None or "shots" not in shot_plan):
            global_style = shot_plan or {}
            base_prompt = shot.get("visual_template") or shot.get("visual", "")
            prompt = self._enhance_prompt_with_style(base_prompt, global_style)
            prompt = self._add_camera_instructions(prompt, shot.get("camera", ""))
            prompt = self._add_duration_hint(prompt, shot.get("duration_s", 0))
            return prompt

        ir = ir or {}
        shot_plan = shot_plan or {}
        from src.config.constants import QUALITY_MODES

        # Validate shot count against quality mode limits
        mode_config = QUALITY_MODES.get(quality_mode, QUALITY_MODES["balanced"])
        max_shots = mode_config["max_shots"]

        shots = shot_plan.get("shots", [])
        if len(shots) > max_shots:
            raise ValueError(
                f"Shot count {len(shots)} exceeds quality mode limit ({max_shots}). "
                f"Use higher quality mode or reduce shot count."
            )

        # Extract global settings
        global_style = shot_plan.get("global", shot_plan.get("global_style", {}))
        visual_style = global_style.get("style", global_style.get("visual", "电影感写实"))
        lighting = global_style.get("lighting", "自然光")
        color_tone = global_style.get("color_tone", "自然色调")

        # Extract scene and emotion
        scene = ir.get("scene", {})
        scene_desc = f"{scene.get('location', '室内')}、{scene.get('time', '日')}"
        emotion_curve = ir.get("emotion_curve", ["平静"])
        emotion_desc = "、".join(emotion_curve)

        # Extract subtitle policy
        subtitle_policy = shot_plan.get("subtitle_policy", "none")

        # Compile global requirements section
        global_requirements = self._render_template(
            self.GLOBAL_REQUIREMENTS_TEMPLATE,
            {
                "visual_style": visual_style,
                "lighting": lighting,
                "color_tone": color_tone,
                "scene_desc": scene_desc,
                "emotion_desc": emotion_desc,
                "subtitle_policy": subtitle_policy,
            }
        )

        # Compile shot script section
        shot_id = shot.get("shot_id", 1)
        duration_s = shot.get("duration_s", 5)

        # Calculate start and end time based on shot sequence
        shots = shot_plan.get("shots", [])
        start_time = sum(s.get("duration_s", 0) for s in shots if s.get("shot_id") < shot_id)
        end_time = start_time + duration_s

        shot_description = shot.get("visual", shot.get("visual_template", ""))
        camera_motion = shot.get("camera_motion", "静态")
        shot_script_text = f"{shot_description}，镜头{camera_motion}"

        shot_script = self._render_template(
            self.SHOT_SCRIPT_TEMPLATE,
            {
                "start_time": start_time,
                "end_time": end_time,
                "shot_description": shot_script_text,
            }
        )

        # Compile audio section
        audio = shot.get("audio", {})
        sfx = audio.get("sfx", shot.get("audio_template", "无"))
        narration = audio.get("narration", "")
        narration_language = ir.get("audio", {}).get("narration_language", "中文")
        narration_tone = ir.get("audio", {}).get("narration_tone", "自然")

        audio_section = self._render_template(
            self.AUDIO_TEMPLATE,
            {
                "sfx": sfx,
                "narration_language": narration_language,
                "narration_tone": narration_tone,
                "narration": narration,
            }
        )

        # Compile consistency section
        consistency_notes = self._generate_consistency_notes(ir, shot_plan)
        consistency_section = self._render_template(
            self.CONSISTENCY_TEMPLATE,
            {"consistency_notes": consistency_notes}
        )

        # Combine all sections
        compiled_prompt = "\n".join([
            global_requirements,
            shot_script,
            audio_section,
            consistency_section,
        ])

        # Compile negative prompt
        compiled_negative_prompt = self._compile_negative_prompt(
            negative_prompt_base,
            shot,
            ir,
            subtitle_policy,
        )

        # Build generation parameters
        resolution = ir.get("resolution", "1280x720").replace("x", "*")
        params = {
            "model": "wan2.6-t2v",
            "size": resolution,
            "duration": duration_s,
            "seed": self._generate_seed(),
            "prompt_extend": prompt_extend,
            "watermark": ir.get("watermark", False),
        }

        return CompiledPrompt(
            compiled_prompt=compiled_prompt,
            compiled_negative_prompt=compiled_negative_prompt,
            params=params,
        )

    def compile_negative_prompt(self) -> str:
        """Compile a baseline negative prompt."""
        return "blurry, distorted, low quality, artifacts"

    def compile_shot_prompts(self, shot_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Compile prompts for all shots in a plan."""
        compiled = []
        global_style = shot_plan.get("global_style", shot_plan.get("global", {}))
        for shot in shot_plan.get("shots", []):
            prompt = self.compile_shot_prompt(shot, global_style)
            compiled.append(
                {
                    "shot_id": shot.get("shot_id"),
                    "compiled_prompt": prompt,
                    "compiled_negative_prompt": self.compile_negative_prompt(),
                }
            )
        return compiled

    def compile_shot_requests(
        self,
        shot_plan: Dict[str, Any],
        resolution: str = "1280*720",
        fps: int = 30,
    ) -> List[Dict[str, Any]]:
        """Compile shot requests with params for generation."""
        prompts = self.compile_shot_prompts(shot_plan)
        requests = []
        for shot, compiled in zip(shot_plan.get("shots", []), prompts):
            params = {
                "size": resolution,
                "duration": shot.get("duration_s", 0),
                "fps": fps,
                "seed": self._generate_seed(),
            }
            requests.append(
                {
                    **compiled,
                    "params": params,
                }
            )
        return requests

    def _compile_negative_prompt(
        self,
        negative_prompt_base: str,
        shot: Dict[str, Any],
        ir: Dict[str, Any],
        subtitle_policy: str,
    ) -> str:
        """
        Compile negative prompt with base and scenario-specific additions

        Args:
            negative_prompt_base: Base negative prompt from template
            shot: Shot dictionary
            ir: Intermediate Representation
            subtitle_policy: Subtitle policy

        Returns:
            Compiled negative prompt
        """
        base_terms = [negative_prompt_base]

        # Add subtitle policy specific terms
        if subtitle_policy == "none":
            base_terms.extend(["text", "subtitles", "watermark", "logo"])

        # Add quality terms
        quality_terms = ["low quality", "blurry", "out of focus", "deformed"]
        base_terms.extend(quality_terms)

        # Add scenario-specific terms
        scenario_terms = self._get_scenario_negative_terms(shot, ir)
        base_terms.extend(scenario_terms)

        return ", ".join(base_terms)

    def _get_scenario_negative_terms(
        self,
        shot: Dict[str, Any],
        ir: Dict[str, Any],
    ) -> List[str]:
        """
        Get scenario-specific negative prompt terms

        Args:
            shot: Shot dictionary
            ir: Intermediate Representation

        Returns:
            List of negative terms
        """
        terms = []

        # Avoid common issues
        terms.extend([
            "distortion",
            "artifacts",
            "flickering",
            "inconsistent characters",
        ])

        return terms

    def _enhance_prompt_with_style(self, base_prompt: str, style: Dict[str, Any]) -> str:
        """Enhance base prompt with style descriptors."""
        style_parts = [
            style.get("visual"),
            style.get("color_tone"),
            style.get("lighting"),
        ]
        style_text = "、".join([s for s in style_parts if s])
        if style_text:
            return f"{base_prompt}，{style_text}"
        return base_prompt

    def _add_camera_instructions(self, base_prompt: str, camera: str) -> str:
        """Add camera instructions to prompt."""
        if camera:
            return f"{base_prompt}，镜头{camera}"
        return base_prompt

    def _add_duration_hint(self, base_prompt: str, duration_s: int) -> str:
        """Add duration hint to prompt."""
        if duration_s:
            return f"{base_prompt}，时长{duration_s}s"
        return base_prompt

    def _generate_consistency_notes(
        self,
        ir: Dict[str, Any],
        shot_plan: Dict[str, Any],
    ) -> str:
        """
        Generate consistency notes for the prompt

        Args:
            ir: Intermediate Representation
            shot_plan: Shot plan

        Returns:
            Consistency notes string
        """
        notes = []

        # Character consistency
        characters = ir.get("characters", [])
        if characters:
            notes.append("人物一致")

        # Quality notes
        notes.append("肤色自然")
        notes.append("画面清晰")
        notes.append("不过度抖动")

        # Style consistency
        global_style = shot_plan.get("global", {})
        style = global_style.get("style", "")
        if style:
            notes.append(f"保持{style}风格")

        return "、".join(notes)

    def _generate_seed(self) -> int:
        """
        Generate random seed for generation

        Returns:
            Random seed integer
        """
        import random
        return random.randint(1, 2**31 - 1)

    def _render_template(
        self,
        template_string: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Render Jinja2 template with context

        Args:
            template_string: Template string
            context: Template context variables

        Returns:
            Rendered string
        """
        template = self.jinja_env.from_string(template_string)
        return template.render(**context)

    def validate_compiled_prompt(
        self,
        compiled_prompt: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate compiled prompt has all 4 required sections in order

        Args:
            compiled_prompt: Compiled prompt string

        Returns:
            Tuple of (is_valid, error_message)
        """
        required_sections = [
            "全片要求",
            "镜头脚本",
            "音频",
            "一致性",
        ]

        # Check all sections present
        for section in required_sections:
            if section not in compiled_prompt:
                return False, f"Missing required section: {section}"

        # Check sections are in order
        section_positions = {}
        for section in required_sections:
            pos = compiled_prompt.find(section)
            if pos == -1:
                return False, f"Section not found: {section}"
            section_positions[section] = pos

        # Verify order
        section_names = list(section_positions.keys())
        positions = list(section_positions.values())
        if positions != sorted(positions):
            return False, "Sections not in correct order"

        return True, None

    def validate_negative_prompt(
        self,
        negative_prompt: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate negative prompt contains required components

        Args:
            negative_prompt: Negative prompt string

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if not empty
        if not negative_prompt or not negative_prompt.strip():
            return False, "Negative prompt cannot be empty"

        # Check for base negative terms
        required_terms = ["text", "subtitles"]
        missing_terms = [term for term in required_terms if term.lower() not in negative_prompt.lower()]

        if missing_terms:
            return False, f"Negative prompt missing required terms: {', '.join(missing_terms)}"

        return True, None
