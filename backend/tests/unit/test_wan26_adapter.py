"""
Unit Tests for WAN26 Adapter
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.core.wan26_adapter import (
    Wan26Adapter,
    Wan26RetryAdapter,
    ShotGenerationRequest,
    ShotGenerationResponse
)


class TestShotGenerationRequest:
    """Test suite for ShotGenerationRequest model"""

    def test_create_request_valid(self):
        """Test creating valid shot generation request"""
        request = ShotGenerationRequest(
            prompt="测试提示词",
            negative_prompt="负面提示词",
            size="1280*720",
            duration=5,
            seed=12345
        )

        assert request.prompt == "测试提示词"
        assert request.negative_prompt == "负面提示词"
        assert request.size == "1280*720"
        assert request.duration == 5
        assert request.seed == 12345
        assert request.prompt_extend is False
        assert request.watermark is False

    def test_create_request_with_optional_params(self):
        """Test creating request with optional parameters"""
        request = ShotGenerationRequest(
            prompt="测试提示词",
            negative_prompt="",
            size="1920*1080",
            duration=10,
            seed=54321,
            prompt_extend=True,
            watermark=True
        )

        assert request.prompt_extend is True
        assert request.watermark is True


class TestWan26Adapter:
    """Test suite for Wan26Adapter"""

    @pytest.fixture
    def adapter(self, mock_env_vars):
        """Create Wan26Adapter instance with test environment"""
        from src.config.settings import settings
        return Wan26Adapter()

    @pytest.mark.asyncio
    async def test_submit_shot_request_success(self, adapter: Wan26Adapter):
        """Test successful shot request submission"""
        request = ShotGenerationRequest(
            prompt="测试视频生成",
            negative_prompt="",
            size="1280*720",
            duration=5,
            seed=12345
        )

        # Mock DashScope VideoSynthesis.async_call
        with patch('src.core.wan26_adapter.VideoSynthesis') as mock_video:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.output.task_id = "test_task_123"
            mock_video.async_call.return_value = mock_response

            response = await adapter.submit_shot_request(request)

            assert response.task_id == "test_task_123"
            assert response.status == "submitted"
            assert response.video_url is None
            assert response.error is None

    @pytest.mark.asyncio
    async def test_submit_shot_request_failure(self, adapter: Wan26Adapter):
        """Test shot request submission failure"""
        request = ShotGenerationRequest(
            prompt="测试视频生成",
            negative_prompt="",
            size="1280*720",
            duration=5,
            seed=12345
        )

        # Mock DashScope failure
        with patch('src.core.wan26_adapter.VideoSynthesis') as mock_video:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.code = "InvalidParameter"
            mock_response.message = "Invalid prompt"
            mock_video.async_call.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                await adapter.submit_shot_request(request)

            assert "Failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_poll_task_status_success(self, adapter: Wan26Adapter):
        """Test successful task status polling"""
        # Mock VideoSynthesis.wait
        with patch('src.core.wan26_adapter.VideoSynthesis') as mock_video:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.output.video_url = "https://example.com/video.mp4"

            # Create mock task object
            mock_task = Mock()
            mock_task.task_id = "test_task_123"

            mock_video.wait.return_value = mock_response

            response = await adapter.poll_task_status("test_task_123")

            assert response.task_id == "test_task_123"
            assert response.status == "succeeded"
            assert response.video_url == "https://example.com/video.mp4"

    @pytest.mark.asyncio
    async def test_poll_task_status_failed(self, adapter: Wan26Adapter):
        """Test failed task status polling"""
        # Mock VideoSynthesis.wait with failure
        with patch('src.core.wan26_adapter.VideoSynthesis') as mock_video:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.code = "InternalError"
            mock_response.message = "Generation failed"

            mock_task = Mock()
            mock_task.task_id = "test_task_123"

            mock_video.wait.return_value = mock_response

            response = await adapter.poll_task_status("test_task_123")

            assert response.status == "failed"
            assert response.error is not None


class TestWan26RetryAdapter:
    """Test suite for Wan26RetryAdapter"""

    @pytest.fixture
    def retry_adapter(self, mock_env_vars):
        """Create Wan26RetryAdapter instance"""
        from src.config.settings import settings
        return Wan26RetryAdapter()

    @pytest.mark.asyncio
    async def test_submit_with_retry_success_on_first_try(self, retry_adapter: Wan26RetryAdapter):
        """Test successful submission on first attempt"""
        request = ShotGenerationRequest(
            prompt="测试视频生成",
            negative_prompt="",
            size="1280*720",
            duration=5,
            seed=12345
        )

        with patch('src.core.wan26_adapter.VideoSynthesis') as mock_video:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.output.task_id = "test_task_123"
            mock_video.async_call.return_value = mock_response

            response = await retry_adapter.submit_shot_request_with_retry(request)

            assert response.task_id == "test_task_123"
            assert mock_video.async_call.call_count == 1

    @pytest.mark.asyncio
    async def test_submit_with_retry_success_after_retry(self, retry_adapter: Wan26RetryAdapter):
        """Test successful submission after retry"""
        request = ShotGenerationRequest(
            prompt="测试视频生成",
            negative_prompt="",
            size="1280*720",
            duration=5,
            seed=12345
        )

        with patch('src.core.wan26_adapter.VideoSynthesis') as mock_video:
            # First call fails with timeout
            mock_error_response = Mock()
            mock_error_response.status_code = 504

            # Second call succeeds
            mock_success_response = Mock()
            mock_success_response.status_code = 200
            mock_success_response.output.task_id = "test_task_123"

            mock_video.async_call.side_effect = [
                Exception("Timeout"),
                mock_success_response
            ]

            response = await retry_adapter.submit_shot_request_with_retry(request)

            assert response.task_id == "test_task_123"
            assert mock_video.async_call.call_count == 2

    def test_is_retryable_error_timeout(self, retry_adapter: Wan26RetryAdapter):
        """Test retryable error detection for timeout"""
        error = Exception("Request timeout")
        assert retry_adapter._is_retryable_error(error)

    def test_is_retryable_error_connection(self, retry_adapter: Wan26RetryAdapter):
        """Test retryable error detection for connection error"""
        error = Exception("Connection refused")
        assert retry_adapter._is_retryable_error(error)

    def test_is_retryable_error_non_retryable(self, retry_adapter: Wan26RetryAdapter):
        """Test non-retryable error detection"""
        error = Exception("Invalid API key")
        assert not retry_adapter._is_retryable_error(error)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
