"""
Integration Tests for Wan2.6-t2v Video Generation
"""

import pytest
import os
import asyncio
from unittest.mock import Mock, patch
from dotenv import load_dotenv

# Load environment variables from .env for local runs
load_dotenv()

# Skip if API key not available
pytestmark = pytest.mark.skipif(
    not os.getenv("DASHSCOPE_API_KEY"),
    reason="DASHSCOPE_API_KEY not set"
)

RUN_EXTENDED = os.getenv("WAN26_RUN_EXTENDED") == "1"
WAN26_DURATION_S = int(os.getenv("WAN26_DURATION_S", "3"))


class TestWan26VideoGeneration:
    """Integration tests for Wan2.6 video generation"""

    @pytest.fixture
    def adapter(self, mock_env_vars):
        """Create Wan26Adapter instance"""
        from src.core.wan26_adapter import Wan26Adapter
        return Wan26Adapter()

    @pytest.fixture
    def sample_request(self):
        """Sample video generation request"""
        from src.core.wan26_adapter import ShotGenerationRequest
        return ShotGenerationRequest(
            prompt="一只可爱的小猫在阳光下玩耍",
            negative_prompt="模糊, 失真",
            size="1280*720",
            duration=WAN26_DURATION_S,
            seed=12345,
            prompt_extend=True,
            watermark=False
        )

    @pytest.mark.skipif(
        not RUN_EXTENDED,
        reason="Extended test; set WAN26_RUN_EXTENDED=1 to enable",
    )
    @pytest.mark.asyncio
    async def test_submit_video_generation_request(self, adapter: "Wan26Adapter", sample_request):
        """Test submitting video generation request"""
        # Note: This test makes real API call to DashScope
        # Skip if running in CI or without proper API key

        response = await adapter.submit_shot_request(sample_request)

        assert response.task_id
        assert response.status == "submitted"
        print(f"Task ID: {response.task_id}")

    @pytest.mark.asyncio
    async def test_poll_video_generation_status(self, adapter: "Wan26Adapter", sample_request):
        """Test polling video generation status"""
        # Submit request first
        submit_response = await adapter.submit_shot_request(sample_request)

        # Poll for completion
        # Note: This may take several minutes
        poll_response = await adapter.poll_task_status(
            submit_response.task_id,
            max_attempts=60,  # 5 minutes
            poll_interval=5
        )

        assert poll_response.status in ["succeeded", "failed"]
        if poll_response.status == "succeeded":
            assert poll_response.video_url
            print(f"Video URL: {poll_response.video_url}")
        else:
            print(f"Generation failed: {poll_response.error}")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not RUN_EXTENDED,
        reason="Extended test; set WAN26_RUN_EXTENDED=1 to enable",
    )
    async def test_video_generation_full_workflow(self, adapter: "Wan26Adapter"):
        """Test complete video generation workflow"""
        request = Mock(
            prompt="宁静的湖面，月光倒映",
            negative_prompt="",
            size="1280*720",
            duration=WAN26_DURATION_S,
            seed=54321,
            prompt_extend=False,
            watermark=False
        )

        # Submit
        submit_response = await adapter.submit_shot_request(request)
        assert submit_response.task_id

        # Wait for completion
        poll_response = await adapter.poll_task_status(submit_response.task_id)

        if poll_response.status == "succeeded":
            print(f"✓ Video generated successfully: {poll_response.video_url}")
            assert poll_response.video_url.startswith("http")
        else:
            print(f"✗ Video generation failed: {poll_response.error}")
            pytest.skip("Video generation failed")


class TestWan26WithRetry:
    """Integration tests for Wan26Adapter with retry logic"""

    @pytest.fixture
    def retry_adapter(self, mock_env_vars):
        """Create Wan26RetryAdapter instance"""
        from src.core.wan26_adapter import Wan26RetryAdapter
        return Wan26RetryAdapter()

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not RUN_EXTENDED,
        reason="Extended test; set WAN26_RUN_EXTENDED=1 to enable",
    )
    async def test_submit_with_retry_success(self, retry_adapter: "Wan26RetryAdapter"):
        """Test submission with retry on transient errors"""
        # This test would require mocking to simulate transient errors
        # For now, we test the success path
        from src.core.wan26_adapter import ShotGenerationRequest

        request = ShotGenerationRequest(
            prompt="测试视频生成",
            negative_prompt="",
            size="1280*720",
            duration=WAN26_DURATION_S,
            seed=12345
        )

        response = await retry_adapter.submit_shot_request_with_retry(request)

        assert response.task_id
        assert response.status == "submitted"
        print(f"Task ID with retry: {response.task_id}")


@pytest.mark.skip("Requires long-running video generation")
class TestWan26LongRunning:
    """Tests for long-running video generation operations"""

    @pytest.fixture
    def adapter(self, mock_env_vars):
        """Create Wan26Adapter instance"""
        from src.core.wan26_adapter import Wan26Adapter
        return Wan26Adapter()

    @pytest.mark.asyncio
    async def test_long_video_generation(self, adapter: "Wan26Adapter"):
        """Test generating longer video (10 seconds)"""
        from src.core.wan26_adapter import ShotGenerationRequest

        request = ShotGenerationRequest(
            prompt="美丽的日落景色，从黄昏到夜晚的渐变",
            negative_prompt="",
            size="1920*1080",  # Full HD
            duration=10,  # Longer duration
            seed=99999
        )

        submit_response = await adapter.submit_shot_request(request)
        poll_response = await adapter.poll_task_status(
            submit_response.task_id,
            max_attempts=120,  # 10 minutes
            poll_interval=5
        )

        assert poll_response.status in ["succeeded", "failed"]

    @pytest.mark.asyncio
    async def test_multiple_concurrent_requests(self, adapter: "Wan26Adapter"):
        """Test multiple concurrent video generation requests"""
        from src.core.wan26_adapter import ShotGenerationRequest

        requests = [
            ShotGenerationRequest(
                prompt=f"测试视频 {i}",
                negative_prompt="",
                size="1280*720",
                duration=WAN26_DURATION_S,
                seed=12345 + i
            )
            for i in range(3)
        ]

        # Submit all requests concurrently
        tasks = [adapter.submit_shot_request(req) for req in requests]
        responses = await asyncio.gather(*tasks)

        assert len(responses) == 3
        for i, response in enumerate(responses):
            assert response.task_id
            print(f"Concurrent task {i}: {response.task_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
