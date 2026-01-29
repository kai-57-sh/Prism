"""
Integration Tests for Qwen LLM
"""

import pytest
import os
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

# Skip these tests if API keys are not available
pytestmark = pytest.mark.skipif(
    not os.getenv("MODELSCOPE_API_KEY"),
    reason="MODELSCOPE_API_KEY not set"
)


class TestQwenLLMIntegration:
    """Integration tests for Qwen LLM via ModelScope"""

    @pytest.fixture
    def llm(self, mock_env_vars):
        """Create ChatOpenAI instance for Qwen"""
        from src.config.settings import settings
        return ChatOpenAI(
            model=settings.qwen_model,
            api_key=settings.modelscope_api_key,
            base_url=settings.modelscope_base_url,
            temperature=0.0,
        )

    def test_basic_qwen_call(self, llm):
        """Test basic Qwen model call"""
        messages = [HumanMessage(content="你好，请用一句话介绍你自己。")]

        response = llm.invoke(messages)

        assert response.content
        assert len(response.content) > 0
        print(f"Qwen Response: {response.content}")

    def test_qwen_with_system_message(self, llm):
        """Test Qwen with system message"""
        messages = [
            SystemMessage(content="你是一个医疗视频生成助手。"),
            HumanMessage(content="请生成一个关于失眠的简短描述。")
        ]

        response = llm.invoke(messages)

        assert response.content
        assert "失眠" in response.content or "睡眠" in response.content
        print(f"Qwen Response: {response.content}")

    def test_qwen_json_output(self, llm):
        """Test Qwen JSON output"""
        prompt = """请以 JSON 格式返回以下信息：
{
    "topic": "失眠",
    "intent": "mood_video",
    "emotion": ["焦虑", "平静"]
}

只返回 JSON，不要其他内容。"""

        messages = [HumanMessage(content=prompt)]
        response = llm.invoke(messages)

        assert response.content
        print(f"Qwen JSON Response: {response.content}")

        # Try to parse JSON
        import json
        try:
            parsed = json.loads(response.content)
            assert "topic" in parsed
            assert "intent" in parsed
        except json.JSONDecodeError:
            pytest.fail("Failed to parse JSON response")

    def test_qwen_chinese_understanding(self, llm):
        """Test Qwen Chinese understanding"""
        messages = [
            HumanMessage(content="请将'焦虑'、'失眠'、'放松'这三个词按情绪从负面到正面排序。")
        ]

        response = llm.invoke(messages)

        assert response.content
        print(f"Qwen Chinese Response: {response.content}")

    def test_qwen_structured_extraction(self, llm):
        """Test Qwen structured information extraction"""
        user_input = "我想要一个关于失眠的舒缓视频，时长 10 秒，暖色调"

        prompt = f"""从以下用户输入中提取结构化信息：

用户输入: {user_input}

请以 JSON 格式返回：
{{
    "topic": "主题",
    "intent": "意图",
    "duration_preference_s": 时长（数字），
    "color_tone": "色调"
}}

只返回 JSON。"""

        messages = [HumanMessage(content=prompt)]
        response = llm.invoke(messages)

        assert response.content
        print(f"Qwen Extraction Response: {response.content}")

        import json
        try:
            parsed = json.loads(response.content)
            assert parsed["topic"] == "失眠" or "失眠" in parsed["topic"]
            assert parsed["duration_preference_s"] == 10
        except json.JSONDecodeError:
            pytest.fail("Failed to parse extraction JSON")


class TestLLMOrchestratorIntegration:
    """Integration tests for LLM Orchestrator with real LLM"""

    @pytest.fixture
    def orchestrator(self, mock_env_vars):
        """Create LLMOrchestrator instance"""
        from src.core.llm_orchestrator import LLMOrchestrator
        return LLMOrchestrator()

    def test_parse_ir_simple(self, orchestrator):
        """Test IR parsing with simple input"""
        user_input = "我想要一个关于失眠的舒缓视频"

        ir = orchestrator.parse_ir(user_input, quality_mode="balanced")

        assert ir.topic
        assert ir.intent
        assert ir.duration_preference_s > 0
        assert ir.quality_mode == "balanced"
        print(f"Parsed IR: {ir}")

    def test_parse_ir_detailed(self, orchestrator):
        """Test IR parsing with detailed input"""
        user_input = """我想要一个10秒的视频，主题是失眠治疗。
风格要舒缓、暖色调。场景设定在卧室。
情绪从焦虑逐渐转为平静。不需要字幕。"""

        ir = orchestrator.parse_ir(user_input, quality_mode="high")

        assert ir.topic == "失眠" or "失眠" in ir.topic
        assert ir.style
        assert ir.style.get("color_tone") == "暖色调" or "暖" in ir.style.get("color_tone", "")
        assert ir.scene
        assert ir.scene.get("location") == "卧室" or "卧室" in ir.scene.get("location", "")
        assert len(ir.emotion_curve) >= 2
        assert ir.duration_preference_s == 10
        print(f"Detailed IR: {ir}")

    def test_instantiate_template(self, orchestrator, sample_template):
        """Test template instantiation"""
        from src.core.llm_orchestrator import IR

        ir = IR(
            topic="失眠",
            intent="mood_video",
            style={"visual": "舒缓", "color_tone": "暖色调"},
            scene={"location": "卧室", "time": "夜晚"},
            characters=[],
            emotion_curve=["焦虑", "平静", "安详"],
            subtitle_policy="none",
            audio={"mode": "tts", "narration_language": "zh-CN"},
            duration_preference_s=10,
            quality_mode="balanced",
        )

        shot_plan = orchestrator.instantiate_template(ir, sample_template)

        assert shot_plan.template_id == sample_template["template_id"]
        assert shot_plan.template_version == sample_template["version"]
        assert len(shot_plan.shots) == len(sample_template["shot_skeletons"])

        # Check that shots have concrete values
        for shot in shot_plan.shots:
            assert "compiled_prompt" in shot or shot.get("visual_template")
            assert shot["duration_s"] > 0

        print(f"Shot Plan: {shot_plan}")

    def test_feedback_parser(self):
        """Test feedback parsing"""
        from src.core.llm_orchestrator import FeedbackParser
        previous_ir = {
            "topic": "失眠",
            "intent": "mood_video",
            "style": {"visual": "舒缓"},
            "scene": {"location": "卧室"},
            "characters": [],
            "emotion_curve": ["焦虑", "平静"],
            "subtitle_policy": "none",
            "audio": {"mode": "tts"},
            "duration_preference_s": 10,
            "quality_mode": "balanced"
        }

        feedback = "镜头太晃动了，希望稳定一些。旁白也太长了。"

        parser = FeedbackParser()
        result = parser.parse_feedback(feedback, previous_ir)

        assert "targeted_fields" in result
        assert "suggested_modifications" in result
        assert len(result["targeted_fields"]) > 0
        print(f"Feedback Result: {result}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
