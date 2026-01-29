"""
Unit Tests for Rate Limiter
"""

import pytest
import time
from unittest.mock import Mock
from src.services.rate_limiter import RateLimiter, RateLimitError


class TestRateLimiter:
    """Test suite for RateLimiter"""

    @pytest.fixture
    def redis_client(self):
        """Mock Redis client"""
        return Mock()

    @pytest.fixture
    def limiter(self, redis_client):
        """Create RateLimiter instance"""
        return RateLimiter(
            redis_client=redis_client,
            requests_per_minute=10,
            burst=10,
            window_seconds=60
        )

    def test_check_rate_limit_within_limit(self, limiter: RateLimiter, redis_client):
        """Test rate limit check when within limit"""
        redis_client.get.return_value = None
        redis_client.incr.return_value = 1

        # Should not raise
        limiter.check_rate_limit("192.168.1.1")

    def test_check_rate_limit_exceeded(self, limiter: RateLimiter, redis_client):
        """Test rate limit check when limit exceeded"""
        redis_client.get.return_value = None
        redis_client.incr.return_value = 11  # Exceeds limit of 10

        with pytest.raises(RateLimitError) as exc_info:
            limiter.check_rate_limit("192.168.1.1")

        assert "rate limit" in str(exc_info.value).lower()

    def test_check_concurrent_jobs_within_limit(self, limiter: RateLimiter, redis_client):
        """Test concurrent job check when within limit"""
        redis_client.get.return_value = "2"  # 2 active jobs

        # Should not raise (max is 5)
        limiter.check_concurrent_jobs("192.168.1.1", max_concurrent=5)

    def test_check_concurrent_jobs_exceeded(self, limiter: RateLimiter, redis_client):
        """Test concurrent job check when limit exceeded"""
        redis_client.get.return_value = "5"  # Already at max

        with pytest.raises(RateLimitError) as exc_info:
            limiter.check_concurrent_jobs("192.168.1.1", max_concurrent=5)

        assert "concurrent" in str(exc_info.value).lower()

    def test_increment_request_count(self, limiter: RateLimiter, redis_client):
        """Test incrementing request count"""
        redis_client.incr.return_value = 3

        count = limiter.increment_request_count("192.168.1.1")

        assert count == 3
        redis_client.incr.assert_called_once()
        redis_client.expire.assert_called_once()

    def test_increment_job_count(self, limiter: RateLimiter, redis_client):
        """Test incrementing job count"""
        redis_client.incr.return_value = 2

        count = limiter.increment_job_count("192.168.1.1")

        assert count == 2
        redis_client.incr.assert_called_once()

    def test_decrement_job_count(self, limiter: RateLimiter, redis_client):
        """Test decrementing job count"""
        limiter.decrement_job_count("192.168.1.1")
        redis_client.decr.assert_called_once()

    def test_get_request_count(self, limiter: RateLimiter, redis_client):
        """Test getting request count"""
        redis_client.get.return_value = "5"

        count = limiter.get_request_count("192.168.1.1")

        assert count == 5

    def test_get_request_count_no_requests(self, limiter: RateLimiter, redis_client):
        """Test getting request count when no requests"""
        redis_client.get.return_value = None

        count = limiter.get_request_count("192.168.1.1")

        assert count == 0

    def test_get_job_count(self, limiter: RateLimiter, redis_client):
        """Test getting job count"""
        redis_client.get.return_value = "3"

        count = limiter.get_job_count("192.168.1.1")

        assert count == 3

    def test_reset_rate_limit(self, limiter: RateLimiter, redis_client):
        """Test resetting rate limit"""
        limiter.reset_rate_limit("192.168.1.1")
        redis_client.delete.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
