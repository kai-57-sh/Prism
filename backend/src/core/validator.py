"""
Validator - Parameter validation, medical compliance, and subtitle policy enforcement
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Union
from pydantic import BaseModel, Field, validator

from src.config.constants import (
    SUPPORTED_LANGUAGES,
    MIN_DURATION_S,
    MAX_DURATION_S,
    MIN_SHOT_DURATION_S,
    MAX_SHOT_DURATION_S,
    SUPPORTED_RESOLUTIONS,
    WATERMARK_OPTIONS,
    SUBTITLE_POLICY_OPTIONS,
    QUALITY_MODES,
)


class ValidationError(Exception):
    """Validation error with suggested modifications"""

    def __init__(self, message: str, code: str, suggested_modifications: Optional[List[str]] = None):
        self.message = message
        self.code = code
        self.suggested_modifications = suggested_modifications or []
        super().__init__(self.message)


@dataclass
class ValidationResult:
    """Validation result for unit tests and lightweight checks."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_compliant(self) -> bool:
        return self.is_valid


class Validator:
    """
    Validate generation parameters with medical compliance and auto-fix
    """

    # Medical content violation vocabulary
    ABSOLUTE_EFFICACY_PHRASES = [
        "guaranteed cure", "100% effective", "immediate results",
        "absolute cure", "complete recovery guaranteed",
    ]

    SUBSTITUTE_MEDICAL_ADVICE_PHRASES = [
        "don't go to hospital", "ignore doctor's orders",
        "skip medical treatment", "avoid doctors",
    ]

    MEDICAL_ADVICE_PHRASES = [
        "服用", "安眠药", "吃药", "药物治疗",
    ]

    def __init__(self):
        """Initialize validator"""
        pass

    def validate_parameters(
        self,
        ir: Dict[str, Any],
        shot_plan: Dict[str, Any],
        quality_mode: str,
    ) -> Tuple[bool, Optional[List[str]]]:
        """
        Validate generation parameters with quality-mode-aware rules

        Args:
            ir: Intermediate Representation
            shot_plan: Shot plan from template
            quality_mode: Quality mode

        Returns:
            Tuple of (is_valid, suggested_modifications)
        """
        from src.config.constants import QUALITY_MODES, VALIDATION_STRICTNESS_LEVELS

        errors = []
        suggestions = []

        # Get quality mode configuration
        if quality_mode not in QUALITY_MODES:
            errors.append(f"Quality mode {quality_mode} not supported")
            return False, suggestions

        mode_config = QUALITY_MODES[quality_mode]
        validation_strictness = mode_config["validation_strictness"]
        strictness_config = VALIDATION_STRICTNESS_LEVELS[validation_strictness]

        # Validate total duration with tolerance
        total_duration = shot_plan.get("duration_s", 0)
        min_duration = MIN_DURATION_S
        max_duration = mode_config.get("max_shot_duration_s", MAX_DURATION_S)

        # Apply tolerance based on strictness
        tolerance_percent = strictness_config["duration_tolerance_percent"]
        duration_tolerance = max_duration * tolerance_percent / 100

        if total_duration < min_duration or total_duration > max_duration + duration_tolerance:
            errors.append(
                f"Total duration {total_duration}s exceeds quality mode limit ({max_duration}s + {duration_tolerance:.1f}s tolerance)"
            )
            suggestions.append(f"Adjust total duration to be between {min_duration}-{max_duration}s for {quality_mode} mode")

        # Validate per-shot durations with mode-specific limits
        shots = shot_plan.get("shots", [])
        max_shots = mode_config["max_shots"]

        if len(shots) > max_shots:
            errors.append(
                f"Shot count {len(shots)} exceeds quality mode limit ({max_shots} shots)"
            )
            suggestions.append(f"Reduce to {max_shots} shots or use higher quality mode")

        for shot in shots:
            shot_duration = shot.get("duration_s", 0)
            min_shot_duration = mode_config.get("min_shot_duration_s", MIN_SHOT_DURATION_S)
            max_shot_duration = mode_config.get("max_shot_duration_s", MAX_SHOT_DURATION_S)

            if shot_duration < min_shot_duration or shot_duration > max_shot_duration:
                errors.append(
                    f"Shot {shot.get('shot_id')} duration {shot_duration}s out of range for {quality_mode} mode [{min_shot_duration}, {max_shot_duration}]"
                )

        # Validate resolution
        resolution = ir.get("resolution", "1280x720")
        if resolution not in SUPPORTED_RESOLUTIONS:
            errors.append(f"Resolution {resolution} not supported")
            suggestions.append(f"Use one of: {', '.join(SUPPORTED_RESOLUTIONS)}")

        # Validate watermark
        watermark = ir.get("watermark", "none")
        if watermark not in WATERMARK_OPTIONS:
            errors.append(f"Watermark {watermark} not supported")

        # Validate subtitle policy based on strictness
        subtitle_policy = shot_plan.get("subtitle_policy", "none")
        if subtitle_policy not in SUBTITLE_POLICY_OPTIONS:
            errors.append(f"Subtitle policy {subtitle_policy} not supported")

        is_valid = len(errors) == 0

        # Apply auto-fix if enabled and validation failed
        if not is_valid and strictness_config["auto_fix_attempts"] > 0:
            # TODO: Implement auto-fix logic
            pass

        if errors and not suggestions:
            suggestions = errors

        return is_valid, suggestions if errors else None

    def validate_shot_plan(
        self,
        shot_plan: Dict[str, Any],
        quality_mode: str = "balanced",
    ) -> ValidationResult:
        """
        Validate shot plan structure and durations.
        """
        errors: List[str] = []
        warnings: List[str] = []

        mode_config = QUALITY_MODES.get(quality_mode, QUALITY_MODES["balanced"])
        shots = shot_plan.get("shots", [])

        max_shots = mode_config["max_shots"]
        if len(shots) > max_shots:
            errors.append(
                f"Shot count {len(shots)} exceeds limit {max_shots} for {quality_mode}"
            )

        total_duration = sum(shot.get("duration_s", 0) for shot in shots)
        if total_duration > MAX_DURATION_S:
            errors.append(
                f"Total duration {total_duration}s exceeds limit {MAX_DURATION_S}s"
            )

        min_shot_duration = mode_config.get("min_shot_duration_s", MIN_SHOT_DURATION_S)
        max_shot_duration = mode_config.get("max_shot_duration_s", MAX_SHOT_DURATION_S)

        for shot in shots:
            if "compiled_prompt" not in shot:
                errors.append(
                    f"Missing compiled prompt for shot {shot.get('shot_id')}"
                )
            shot_duration = shot.get("duration_s", 0)
            if shot_duration < min_shot_duration or shot_duration > max_shot_duration:
                errors.append(
                    f"Shot {shot.get('shot_id')} duration {shot_duration}s out of range"
                )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def compress_narration(
        self,
        narration: str,
        quality_mode: str = "balanced",
    ) -> Tuple[str, Optional[str]]:
        """
        Compress narration text based on quality mode settings

        Args:
            narration: Original narration text
            quality_mode: Quality mode

        Returns:
            Tuple of (compressed_narration, suggested_modification)
        """
        from src.config.constants import QUALITY_MODES, NARRATION_COMPRESSION_LEVELS

        if quality_mode not in QUALITY_MODES:
            quality_mode = "balanced"

        mode_config = QUALITY_MODES[quality_mode]
        max_length = mode_config.get("max_narration_length", 50)
        compression_level = mode_config.get("narration_compression", "standard")
        compression_config = NARRATION_COMPRESSION_LEVELS[compression_level]

        # Check if compression is needed
        if len(narration) <= max_length:
            return narration, None

        # Calculate target length based on compression level
        target_reduction = compression_config["target_reduction_percent"]
        target_length = int(len(narration) * (1 - target_reduction / 100))
        target_length = min(target_length, max_length)

        # Compress narration
        compressed = narration[:target_length].rstrip()

        # Add ellipsis if truncated
        if len(compressed) < len(narration):
            compressed += "..."

        # Simplify language if enabled
        if compression_config["simplify_language"]:
            compressed = self._simplify_language(compressed)

        # Preserve keywords if enabled
        if compression_config["preserve_keywords"]:
            compressed = self._preserve_keywords(compressed, narration)

        suggestion = f"Narration compressed from {len(narration)} to {len(compressed)} characters ({quality_mode} mode)"

        return compressed, suggestion

    def _simplify_language(self, text: str) -> str:
        """
        Simplify language by removing filler words

        Args:
            text: Input text

        Returns:
            Simplified text
        """
        # Remove common filler words
        filler_words = ["um", "uh", "like", "you know", "basically", "actually"]
        words = text.split()
        filtered = [w for w in words if w.lower() not in filler_words and w not in ["...", "??", "!!"]]
        return " ".join(filtered)

    def _preserve_keywords(self, compressed: str, original: str) -> str:
        """
        Preserve important keywords from original text

        Args:
            compressed: Compressed text
            original: Original text

        Returns:
            Text with preserved keywords
        """
        # Extract important words (longer words, numbers, medical terms)
        import re
        keywords = re.findall(r'\b[A-Z][a-z]+\b|\b\d+\b', original)

        # This is a simplified implementation
        # In production, would use more sophisticated keyword extraction
        return compressed

    def validate_medical_compliance(
        self,
        narration_text: str,
        visual_descriptions: Optional[List[str]] = None,
        return_tuple: bool = False,
    ) -> Union[ValidationResult, Tuple[bool, Optional[List[str]]]]:
        """
        Validate medical content compliance

        Args:
            narration_text: Narration text to check
            visual_descriptions: List of visual descriptions

        Returns:
            Tuple of (is_compliant, suggested_modifications)
        """
        violations = []
        suggestions = []

        if visual_descriptions is None:
            visual_descriptions = []

        # Check for absolute efficacy claims
        text_to_check = [narration_text] + visual_descriptions
        for text in text_to_check:
            text_lower = text.lower()

            for phrase in self.ABSOLUTE_EFFICACY_PHRASES:
                if phrase in text_lower:
                    violations.append(f"Absolute efficacy claim detected: '{phrase}'")
                    suggestions.append(f"Remove or soften absolute claim: '{phrase}'")

            for phrase in self.SUBSTITUTE_MEDICAL_ADVICE_PHRASES:
                if phrase in text_lower:
                    violations.append(f"Substitute medical advice detected: '{phrase}'")
                    suggestions.append(f"Remove harmful advice: '{phrase}'")

            for phrase in self.MEDICAL_ADVICE_PHRASES:
                if phrase in text:
                    violations.append(f"Medical advice detected: '{phrase}'")
                    suggestions.append(f"Avoid direct medical advice: '{phrase}'")

        is_compliant = len(violations) == 0

        if return_tuple:
            return is_compliant, suggestions if violations else None

        return ValidationResult(
            is_valid=is_compliant,
            errors=[],
            warnings=suggestions if violations else [],
        )

    def validate_resolution(self, resolution: str) -> bool:
        """Validate resolution with both x and * separators."""
        normalized = resolution.replace("*", "x")
        return normalized in SUPPORTED_RESOLUTIONS

    def validate_seed_count(self, seed_count: int, quality_mode: str) -> bool:
        """Validate seed count by quality mode configuration."""
        mode_config = QUALITY_MODES.get(quality_mode)
        if not mode_config:
            return False
        return seed_count == mode_config.get("preview_seeds")

    def enforce_subtitle_policy(
        self,
        prompt_extend: bool,
        subtitle_policy: str,
        negative_prompt: str,
    ) -> Tuple[str, Optional[str]]:
        """
        Enforce subtitle policy by ensuring negative prompt is appropriate

        Args:
            prompt_extend: Whether prompt extension is enabled
            subtitle_policy: Subtitle policy ('none' or 'allowed')
            negative_prompt: Current negative prompt

        Returns:
            Tuple of (enforced_negative_prompt, error_message)
        """
        required_terms = ["text", "subtitles", "watermark", "logo"]

        if subtitle_policy == "none":
            # Ensure all required terms are present
            missing_terms = [term for term in required_terms if term.lower() not in negative_prompt.lower()]

            if missing_terms:
                # Add missing terms
                additions = ", ".join(missing_terms)
                enforced = f"{negative_prompt}, {additions}"
                return enforced, f"Added required terms to negative prompt: {additions}"

        return negative_prompt, None

    def validate_subtitle_hard_gate(
        self,
        user_input: str,
        subtitle_policy: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Hard gate validation for subtitle policy

        Args:
            user_input: User input text
            subtitle_policy: Requested subtitle policy

        Returns:
            Tuple of (is_allowed, clarification_message)
        """
        # Check if user explicitly requested subtitles
        subtitle_keywords = ["subtitle", "caption", "text on screen", "文字", "字幕"]
        user_input_lower = user_input.lower()

        has_subtitle_request = any(keyword in user_input_lower for keyword in subtitle_keywords)

        if has_subtitle_request and subtitle_policy == "none":
            clarification = (
                "You requested subtitles, but the template's subtitle policy is 'none'. "
                "This template is designed for videos without on-screen text. "
                "Would you like to proceed without subtitles, or choose a different scenario?"
            )
            return False, clarification

        return True, None

    def validate_refinement(
        self,
        feedback: str,
        targeted_fields: List[str],
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate refinement request

        Args:
            feedback: User feedback
            targeted_fields: Fields targeted for revision

        Returns:
            Tuple of (is_valid, error_message)
        """
        valid_fields = {"camera", "narration", "lighting", "emotion", "pacing"}

        # Check if targeted fields are valid
        invalid_fields = [f for f in targeted_fields if f not in valid_fields]

        if invalid_fields:
            return False, f"Invalid targeted fields: {', '.join(invalid_fields)}. Valid fields: {', '.join(valid_fields)}"

        # Check if feedback is too short
        if len(feedback.strip()) < 5:
            return False, "Feedback is too short. Please provide more details."

        return True, None

    def validate_compiled_prompt(
        self,
        compiled_prompt: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate compiled prompt has all required sections

        Args:
            compiled_prompt: Compiled prompt string

        Returns:
            Tuple of (is_valid, error_message)
        """
        required_sections = [
            "全片要求",  # Global requirements
            "镜头脚本",  # Shot script
            "音频",  # Audio
            "一致性",  # Consistency
        ]

        missing_sections = [section for section in required_sections if section not in compiled_prompt]

        if missing_sections:
            return False, f"Missing required sections: {', '.join(missing_sections)}"

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
        required_terms = ["text", "subtitles", "watermark", "logo"]

        missing_terms = [term for term in required_terms if term.lower() not in negative_prompt.lower()]

        if missing_terms:
            return False, f"Negative prompt missing required terms: {', '.join(missing_terms)}"

        return True, None
