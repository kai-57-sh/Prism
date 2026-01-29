"""
Unit Tests for Prompt Compiler
"""

import pytest
from src.core.prompt_compiler import PromptCompiler


class TestPromptCompiler:
    """Test suite for PromptCompiler"""

    @pytest.fixture
    def compiler(self):
        """Create PromptCompiler instance"""
        return PromptCompiler()

    def test_compile_shot_prompt_basic(self, compiler: PromptCompiler):
        """Test basic shot prompt compilation"""
        shot = {
            "shot_id": 1,
            "duration_s": 3,
            "camera": "固定镜头",
            "visual_template": "宁静的卧室场景",
            "audio_template": "轻柔背景音乐"
        }

        global_style = {
            "visual": "舒缓风格",
            "color_tone": "暖色调",
            "lighting": "柔和光线"
        }

        prompt = compiler.compile_shot_prompt(shot, global_style)

        assert "宁静的卧室场景" in prompt
        assert "固定镜头" in prompt
        assert "舒缓风格" in prompt
        assert "暖色调" in prompt
        assert "柔和光线" in prompt

    def test_compile_negative_prompt_basic(self, compiler: PromptCompiler):
        """Test basic negative prompt compilation"""
        negative_prompt = compiler.compile_negative_prompt()

        assert "blurry" in negative_prompt.lower() or "模糊" in negative_prompt.lower()
        assert "distorted" in negative_prompt.lower() or "失真" in negative_prompt.lower()

    def test_compile_shot_prompts_full_plan(self, compiler: PromptCompiler, sample_shot_plan):
        """Test compilation of full shot plan"""
        compiled = compiler.compile_shot_prompts(sample_shot_plan)

        assert len(compiled) == len(sample_shot_plan["shots"])

        for i, shot in enumerate(compiled):
            assert "compiled_prompt" in shot
            assert "compiled_negative_prompt" in shot
            assert shot["compiled_prompt"]
            assert shot["compiled_negative_prompt"]

    def test_enhance_prompt_with_style(self, compiler: PromptCompiler):
        """Test prompt enhancement with style"""
        base_prompt = "卧室场景"
        style = {
            "visual": "写实风格",
            "color_tone": "冷色调",
            "lighting": "自然光"
        }

        enhanced = compiler._enhance_prompt_with_style(base_prompt, style)

        assert "卧室场景" in enhanced
        assert "写实风格" in enhanced
        assert "冷色调" in enhanced
        assert "自然光" in enhanced

    def test_add_camera_instructions(self, compiler: PromptCompiler):
        """Test adding camera instructions to prompt"""
        base_prompt = "卧室场景"
        camera = "缓慢推进"

        with_camera = compiler._add_camera_instructions(base_prompt, camera)

        assert "卧室场景" in with_camera
        assert "缓慢推进" in with_camera

    def test_add_duration_hint(self, compiler: PromptCompiler):
        """Test adding duration hint to prompt"""
        base_prompt = "卧室场景"
        duration = 5

        with_duration = compiler._add_duration_hint(base_prompt, duration)

        assert "卧室场景" in with_duration
        assert "5" in with_duration or "five" in with_duration.lower()

    def test_compile_shot_request(self, compiler: PromptCompiler, sample_shot_plan):
        """Test compilation of complete shot request"""
        shot_requests = compiler.compile_shot_requests(
            sample_shot_plan,
            resolution="1280*720",
            fps=30
        )

        assert len(shot_requests) == len(sample_shot_plan["shots"])

        for req in shot_requests:
            assert "compiled_prompt" in req
            assert "compiled_negative_prompt" in req
            assert "params" in req
            assert req["params"]["size"] == "1280*720"
            assert "seed" in req["params"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
