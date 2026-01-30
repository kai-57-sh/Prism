"""
LLM Orchestrator - LangChain chains for IR parsing and template instantiation
"""

from typing import Dict, Any, List, Optional
from langchain.schema import HumanMessage, SystemMessage
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from src.config.settings import settings
from src.services.observability import logger


# Pydantic models for structured outputs


class IR(BaseModel):
    """Intermediate Representation - Structured output from LLM intent parsing"""

    topic: str = Field(description="Primary topic (e.g., 'insomnia', 'anxiety', 'depression')")
    intent: str = Field(description="User intent (e.g., 'mood_video', 'story_telling')")
    optimized_prompt: str = Field(
        description="LLM-refined prompt that preserves user intent and key details for storyboard writing"
    )
    style: Dict[str, str] = Field(description="Visual style preferences")
    scene: Dict[str, str] = Field(description="Scene setting")
    characters: List[Dict[str, str]] = Field(description="Character descriptions")
    emotion_curve: List[str] = Field(description="Emotional progression across shots")
    subtitle_policy: str = Field(description="Subtitle policy: 'none' or 'allowed'")
    audio: Dict[str, Any] = Field(description="Audio requirements")
    duration_preference_s: int = Field(description="Total duration preference in seconds")
    quality_mode: str = Field(description="Quality mode: 'fast', 'balanced', or 'high'")


class ShotPlan(BaseModel):
    """Shot Plan - Template instantiation result"""

    template_id: str
    template_version: str
    duration_s: int
    subtitle_policy: str
    shots: List[Dict[str, Any]]
    global_style: Dict[str, str]


class LLMOrchestrator:
    """
    Orchestrates LLM chains for IR parsing and template instantiation
    """

    def __init__(self, llm: Optional[Any] = None):
        """Initialize LLM orchestrator using ModelScope OpenAI-compatible endpoint."""
        self.llm = llm

        # Initialize output parsers
        self.ir_parser = PydanticOutputParser(pydantic_object=IR)
        self.shot_plan_parser = PydanticOutputParser(pydantic_object=ShotPlan)

        # Store token usage and duration metrics
        self.metrics = {
            "ir_parse_tokens": 0,
            "ir_parse_duration": 0.0,
            "template_instantiate_tokens": 0,
            "template_instantiate_duration": 0.0,
        }

    def _ensure_llm(self) -> None:
        if self.llm is None:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=settings.qwen_model,
                api_key=settings.modelscope_api_key,
                base_url=settings.modelscope_base_url,
                temperature=0.0,
            )

    def parse_ir(self, user_input: str, quality_mode: str = "balanced") -> IR:
        """
        Parse user input into Intermediate Representation using LLM

        Args:
            user_input: Redacted user input text
            quality_mode: Quality mode (fast, balanced, high)

        Returns:
            IR object
        """
        import time

        start_time = time.time()

        # Build prompt
        prompt = f"""You are a medical video generation assistant. Parse the user's request into a structured Intermediate Representation.

User Request: {user_input}
Quality Mode: {quality_mode}

Extract the following information:
1. topic: Main medical/emotional topic
2. intent: User's goal (e.g., 'mood_video', 'story_telling')
3. optimized_prompt: Rewrite the user request into a concise creative brief for storyboard writing.
   Preserve intent and constraints; do not introduce conflicts or unrelated details.
   Requirements for optimized_prompt:
   - English only: use plain English and avoid non-English words or scripts.
   - No medical advice: do not provide diagnosis, prescriptions, treatment plans, or specific interventions.
   - No absolutes: avoid absolute/guarantee terms (e.g., cure, miracle, guarantee, best, perfect, 100%).
   - No marketing tone: avoid sensationalism, fear, or clickbait; keep calm, objective, trustworthy, warm.
   - Scope: focus on mechanisms, prevention awareness, lifestyle adjustments, and medical history.
   - Prefer neutral terms such as management, improvement, reduce discomfort, support.
4. style: Visual style (visual approach, color tone, lighting)
5. scene: Location and time setting
6. characters: List of characters with type, gender, age_range
7. emotion_curve: List of emotions across shots (start to end)
8. subtitle_policy: 'none' or 'allowed' based on user preference
9. audio: Audio requirements (mode, narration_language, narration_tone, sfx list)
10. duration_preference_s: Total duration in seconds (2-15)
11. quality_mode: '{quality_mode}'

{self.ir_parser.get_format_instructions()}

Ensure all durations are between 2-15 seconds total."""

        try:
            self._ensure_llm()
            messages = [
                SystemMessage(content="You are a medical video generation assistant."),
                HumanMessage(content=prompt),
            ]

            response = self.llm.invoke(messages)

            # Parse structured output
            ir = self.ir_parser.parse(response.content)
            if not ir.optimized_prompt.strip():
                ir.optimized_prompt = user_input

            duration = time.time() - start_time
            self.metrics["ir_parse_duration"] = duration
            # Note: Token usage would be extracted from response if available

            logger.info(
                "ir_parse_success",
                topic=ir.topic,
                intent=ir.intent,
                duration_s=duration,
            )

            return ir

        except Exception as e:
            logger.error("ir_parse_error", error=str(e))
            raise

    def instantiate_template(
        self,
        ir: IR,
        template: Dict[str, Any],
    ) -> ShotPlan:
        """
        Instantiate template with IR values using LLM

        Args:
            ir: Intermediate Representation
            template: Template dictionary with shot_skeletons

        Returns:
            ShotPlan object
        """
        import time

        start_time = time.time()

        # Build prompt
        prompt = f"""You are a medical video director. Instantiate the following template with concrete values based on the user's intent.

**User Intent:**
- Optimized Prompt: {ir.optimized_prompt}
- Topic: {ir.topic}
- Emotion Curve: {', '.join(ir.emotion_curve)}
- Style: {ir.style}
- Scene: {ir.scene}
- Characters: {ir.characters}
- Audio: {ir.audio}
- Duration: {ir.duration_preference_s}s
- Subtitle Policy: {ir.subtitle_policy}

**Template:**
Template ID: {template['template_id']}
Version: {template['version']}

Shot Skeletons:
{self._format_shot_skeletons(template['shot_skeletons'])}

**Instructions (English only):**
1. Use the optimized prompt as the primary creative brief for the storyboard.
2. Fill in template placeholders with concrete values matching the optimized prompt.
3. If any template detail conflicts with the optimized prompt, adapt the template to fit the optimized prompt.
4. Visual style selection (no mixing across shots):
   - If the optimized prompt explicitly specifies a style (vlog, 3D, documentary), follow it.
   - Otherwise choose the most suitable style category:
     a) Patient experience / lifestyle: vlog, real people, daily life, symptom checks; natural light, home/office.
     b) Medical mechanism / explainer: 3D animation, mechanism, metaphor, cute; high-end 3D render, clean studio look.
     c) Medical history / documentary: history, story, year, discovery, black-and-white; retro cinematic chiaroscuro, film grain.
5. Scientific arc across shots (3-shot narrative):
   - Shot 1 (problem): observe a real-world health issue; no excessive pain.
   - Shot 2 (mechanism): explain why it happens scientifically or biologically.
   - Shot 3 (understanding): emphasize knowledge, understanding, or risk awareness only.
     Do NOT imply symptom improvement or health outcomes in Shot 3.
6. Visual prompt constraints (Wan 2.2):
   - Each shot's visual description must be in English and must include the exact keywords:
     "cinematic lighting", "volumetric fog", "720p masterpiece", "high aesthetic score".
   - Use a resolution preference of either "720P" or "1080P" and store it in global_style.resolution_preference.
7. Audio strategy:
   - Narration must be Chinese (colloquial but professional).
   - Strict character limits: Shot 1 <= 12 Chinese characters, Shot 2 <= 24, Shot 3 <= 16.
8. Ensure visual descriptions are detailed and evocative.
9. Match the emotion curve across shots.
10. Respect the subtitle policy.
11. Total duration should be approximately {ir.duration_preference_s}s.

{self.shot_plan_parser.get_format_instructions()}"""

        try:
            self._ensure_llm()
            messages = [
                SystemMessage(content="You are a medical video director."),
                HumanMessage(content=prompt),
            ]

            response = self.llm.invoke(messages)

            # Parse structured output
            shot_plan = self.shot_plan_parser.parse(response.content)

            duration = time.time() - start_time
            self.metrics["template_instantiate_duration"] = duration

            logger.info(
                "template_instantiate_success",
                template_id=shot_plan.template_id,
                shot_count=len(shot_plan.shots),
                duration_s=duration,
            )

            return shot_plan

        except Exception as e:
            logger.error("template_instantiate_error", error=str(e))
            raise

    def _format_shot_skeletons(self, shot_skeletons: List[Dict[str, Any]]) -> str:
        """Format shot skeletons for prompt"""
        formatted = []
        for shot in shot_skeletons:
            formatted.append(f"""
Shot {shot['shot_id']}:
- Duration: {shot['duration_s']}s
- Camera: {shot['camera']}
- Visual Template: {shot['visual_template']}
- Audio Template: {shot['audio_template']}
- Subtitle Policy: {shot['subtitle_policy']}
""")
        return "\n".join(formatted)

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return self.metrics.copy()


class FeedbackParser:
    """
    Parse user feedback to generate IR deltas for revision
    """

    def __init__(self, llm: Optional[Any] = None):
        """Initialize feedback parser using ModelScope OpenAI-compatible endpoint."""
        self.llm = llm

    def _ensure_llm(self) -> None:
        if self.llm is None:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=settings.qwen_model,
                api_key=settings.modelscope_api_key,
                base_url=settings.modelscope_base_url,
                temperature=0.0,
            )

    def parse_feedback(
        self,
        feedback: str,
        previous_ir: IR,
    ) -> Dict[str, Any]:
        """
        Parse user feedback to identify targeted fields for revision

        Args:
            feedback: User's revision feedback
            previous_ir: Original IR from parent job

        Returns:
            Dict with targeted_fields and suggested_modifications
        """
        def _get_ir_value(key: str, default: Any):
            if isinstance(previous_ir, dict):
                return previous_ir.get(key, default)
            return getattr(previous_ir, key, default)

        prompt = f"""You are a medical video revision assistant. Analyze the user's feedback to identify which fields should be modified.

**Previous IR:**
- Topic: {_get_ir_value("topic", "")}
- Intent: {_get_ir_value("intent", "")}
- Style: {_get_ir_value("style", {})}
- Scene: {_get_ir_value("scene", {})}
- Characters: {_get_ir_value("characters", [])}
- Emotion Curve: {_get_ir_value("emotion_curve", [])}

**User Feedback:**
{feedback}

**Instructions:**
Identify which fields should be targeted for revision:
1. camera - Camera work modifications
2. narration - Narration text changes
3. lighting - Lighting adjustments
4. emotion - Emotional tone changes
5. pacing - Speed/timing modifications

Return a JSON object with:
{{
  "targeted_fields": ["camera", "narration"],
  "suggested_modifications": {{
    "camera": "reduce camera shake",
    "narration": "make narration shorter and calmer"
  }}
}}"""

        try:
            self._ensure_llm()
            messages = [
                SystemMessage(content="You are a medical video revision assistant."),
                HumanMessage(content=prompt),
            ]

            response = self.llm.invoke(messages)

            # Parse JSON response
            import json
            result = json.loads(response.content)

            logger.info(
                "feedback_parse_success",
                targeted_fields=result.get("targeted_fields", []),
            )

            return result

        except Exception as e:
            logger.error("feedback_parse_error", error=str(e))
            # Return default target all fields if parsing fails
            return {
                "targeted_fields": ["camera", "narration", "lighting", "emotion", "pacing"],
                "suggested_modifications": {"feedback": feedback},
            }
