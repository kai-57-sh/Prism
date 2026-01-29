"""
End-to-End API Tests
"""

import httpx
import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, AsyncMock

pytestmark = pytest.mark.asyncio


class TestGenerationAPI:
    """E2E tests for /v1/t2v/generate endpoint"""

    @pytest_asyncio.fixture
    async def client(self, test_db_session):
        """Create test client"""
        from src.api.main import app
        from src.models import get_db

        async def override_get_db():
            yield test_db_session

        app.dependency_overrides[get_db] = override_get_db
        await app.router.startup()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
        await app.router.shutdown()
        app.dependency_overrides.clear()

    @pytest.fixture
    def auth_headers(self):
        """Mock authentication headers"""
        return {"X-API-Key": "test-key"}

    async def test_generate_endpoint_accepts_request(
        self,
        client: httpx.AsyncClient,
        auth_headers,
    ):
        """Test that generate endpoint accepts valid request"""
        request_data = {
            "user_prompt": "我想要一个关于失眠的舒缓视频",
            "quality_mode": "balanced",
            "resolution": "1280x720"
        }

        # Mock the job manager to avoid real video generation
        with patch('src.api.routes.generation.JobManager') as mock_job_manager:
            mock_job = Mock(job_id="test_job_123", state="CREATED")
            mock_job_manager.return_value.execute_generation_workflow = AsyncMock(
                return_value=mock_job
            )

            response = await client.post(
                "/v1/t2v/generate",
                json=request_data,
                headers=auth_headers
            )

            # Should accept request (may be 202 or other status)
            assert response.status_code in [200, 201, 202]

            if response.status_code in [200, 201, 202]:
                data = response.json()
                assert "job_id" in data or "message" in data
                print(f"Generate Response: {data}")

    async def test_generate_endpoint_rejects_invalid_resolution(
        self,
        client: httpx.AsyncClient,
        auth_headers,
    ):
        """Test that generate endpoint rejects invalid resolution"""
        request_data = {
            "user_prompt": "测试视频",
            "quality_mode": "balanced",
            "resolution": "640*480"  # Invalid resolution
        }

        response = await client.post(
            "/v1/t2v/generate",
            json=request_data,
            headers=auth_headers
        )

        # Should reject invalid resolution
        assert response.status_code == 400  # Validation error
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    async def test_generate_endpoint_rejects_invalid_quality_mode(
        self,
        client: httpx.AsyncClient,
        auth_headers,
    ):
        """Test that generate endpoint rejects invalid quality mode"""
        request_data = {
            "user_prompt": "测试视频",
            "quality_mode": "invalid_mode",  # Invalid quality mode
            "resolution": "1280*720"
        }

        response = await client.post(
            "/v1/t2v/generate",
            json=request_data,
            headers=auth_headers
        )

        # Should reject invalid quality mode
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    async def test_generate_endpoint_rate_limit_error_format(
        self,
        client: httpx.AsyncClient,
        auth_headers,
    ):
        """Test rate limit error response format."""
        request_data = {
            "user_prompt": "测试视频",
            "quality_mode": "balanced",
            "resolution": "1280x720"
        }

        with patch('src.api.routes.generation.JobManager') as mock_job_manager:
            mock_job_manager.return_value.execute_generation_workflow = AsyncMock(
                side_effect=ValueError("Rate limit exceeded")
            )

            response = await client.post(
                "/v1/t2v/generate",
                json=request_data,
                headers=auth_headers
            )

            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["error"]["code"] == "VALIDATION_ERROR"

    async def test_generate_endpoint_template_match_error_format(
        self,
        client: httpx.AsyncClient,
        auth_headers,
    ):
        """Test template match failure error format."""
        request_data = {
            "user_prompt": "测试视频",
            "quality_mode": "balanced",
            "resolution": "1280x720"
        }

        with patch('src.api.routes.generation.JobManager') as mock_job_manager:
            mock_job_manager.return_value.execute_generation_workflow = AsyncMock(
                side_effect=ValueError("No matching template found. Please provide more details.")
            )

            response = await client.post(
                "/v1/t2v/generate",
                json=request_data,
                headers=auth_headers
            )

            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["error"]["code"] == "VALIDATION_ERROR"

    async def test_generate_endpoint_internal_error_format(
        self,
        client: httpx.AsyncClient,
        auth_headers,
    ):
        """Test internal error response format."""
        request_data = {
            "user_prompt": "测试视频",
            "quality_mode": "balanced",
            "resolution": "1280x720"
        }

        with patch('src.api.routes.generation.JobManager') as mock_job_manager:
            mock_job_manager.return_value.execute_generation_workflow = AsyncMock(
                side_effect=Exception("upstream error")
            )

            response = await client.post(
                "/v1/t2v/generate",
                json=request_data,
                headers=auth_headers
            )

            assert response.status_code == 500
            data = response.json()
            assert data["detail"]["error"]["code"] == "GENERATION_ERROR"


class TestJobsAPI:
    """E2E tests for /v1/t2v/jobs/{job_id} endpoint"""

    @pytest_asyncio.fixture
    async def client(self, test_db_session):
        """Create test client"""
        from src.api.main import app
        from src.models import get_db

        async def override_get_db():
            yield test_db_session

        app.dependency_overrides[get_db] = override_get_db
        await app.router.startup()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
        await app.router.shutdown()
        app.dependency_overrides.clear()

    @pytest.fixture
    def auth_headers(self):
        """Mock authentication headers"""
        return {"X-API-Key": "test-key"}

    async def test_get_job_status(
        self,
        client: httpx.AsyncClient,
        auth_headers,
        test_db_session,
    ):
        """Test retrieving job status"""
        # Create a test job
        from src.services.storage import JobDB

        job = JobDB.create_job(
            db=test_db_session,
            user_input_redacted="测试视频",
            user_input_hash="abc123",
            template_id="template",
            template_version="1.0",
            quality_mode="balanced",
            ir={},
            shot_plan={},
            shot_requests=[],
            external_task_ids=[],
            total_duration_s=3,
            resolution="1280x720",
        )
        JobDB.update_job_state(test_db_session, job.job_id, "RUNNING")

        # Get job status
        response = await client.get(
            f"/v1/t2v/jobs/{job.job_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job.job_id
        assert "status" in data

    async def test_get_job_not_found(self, client: httpx.AsyncClient, auth_headers):
        """Test retrieving non-existent job"""
        response = await client.get(
            "/v1/t2v/jobs/nonexistent_job",
            headers=auth_headers
        )

        assert response.status_code == 404


class TestFinalizeAPI:
    """E2E tests for /v1/t2v/jobs/{job_id}/finalize endpoint"""

    @pytest_asyncio.fixture
    async def client(self, test_db_session):
        """Create test client"""
        from src.api.main import app
        from src.models import get_db

        async def override_get_db():
            yield test_db_session

        app.dependency_overrides[get_db] = override_get_db
        await app.router.startup()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
        await app.router.shutdown()
        app.dependency_overrides.clear()

    @pytest.fixture
    def auth_headers(self):
        """Mock authentication headers"""
        return {"X-API-Key": "test-key"}

    async def test_finalize_job(
        self,
        client: httpx.AsyncClient,
        auth_headers,
        test_db_session,
    ):
        """Test finalizing a job"""
        # Create a completed job
        from src.services.storage import JobDB

        job = JobDB.create_job(
            db=test_db_session,
            user_input_redacted="测试视频",
            user_input_hash="abc123",
            template_id="template",
            template_version="1.0",
            quality_mode="balanced",
            ir={},
            shot_plan={},
            shot_requests=[],
            external_task_ids=[],
            total_duration_s=3,
            resolution="1280x720",
        )
        job.preview_shot_assets = [
            {
                "shot_id": 1,
                "video_url": "https://example.com/video1.mp4",
                "audio_url": "https://example.com/audio1.mp3",
                "duration_s": 3,
                "resolution": "1280x720",
                "seed": 12345,
            }
        ]
        job.shot_assets = [
            {
                "shot_id": 1,
                "video_url": "https://example.com/video1.mp4",
                "audio_url": "https://example.com/audio1.mp3",
                "duration_s": 3,
                "resolution": "1280*720",
                "seed": 12345,
            }
        ]
        job.state = "SUCCEEDED"
        test_db_session.commit()

        request_data = {
            "selected_seeds": {
                "1": 12345
            }
        }

        # Mock job manager
        with patch('src.api.routes.finalize.JobManager') as mock_job_manager:
            mock_job = Mock(job_id="finalized_job_123", state="RUNNING")
            mock_job_manager.return_value.execute_finalization_workflow = AsyncMock(
                return_value=mock_job
            )

            response = await client.post(
                f"/v1/t2v/jobs/{job.job_id}/finalize",
                json=request_data,
                headers=auth_headers
            )

            assert response.status_code == 202
            data = response.json()
            assert "job_id" in data

    async def test_finalize_requires_preview_assets(
        self,
        client: httpx.AsyncClient,
        auth_headers,
        test_db_session,
    ):
        """Finalize should fail without preview assets."""
        from src.services.storage import JobDB

        job = JobDB.create_job(
            db=test_db_session,
            user_input_redacted="test",
            user_input_hash="hash",
            template_id="template",
            template_version="1.0",
            quality_mode="balanced",
            ir={},
            shot_plan={},
            shot_requests=[],
            external_task_ids=[],
            total_duration_s=3,
            resolution="1280x720",
        )
        JobDB.update_job_state(test_db_session, job.job_id, "SUCCEEDED")

        response = await client.post(
            f"/v1/t2v/jobs/{job.job_id}/finalize",
            json={"selected_seeds": {"1": 12345}},
            headers=auth_headers
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "NO_PREVIEW_ASSETS"

    async def test_finalize_invalid_state(
        self,
        client: httpx.AsyncClient,
        auth_headers,
        test_db_session,
    ):
        """Finalize should fail if job is not succeeded."""
        from src.services.storage import JobDB

        job = JobDB.create_job(
            db=test_db_session,
            user_input_redacted="test",
            user_input_hash="hash",
            template_id="template",
            template_version="1.0",
            quality_mode="balanced",
            ir={},
            shot_plan={},
            shot_requests=[],
            external_task_ids=[],
            total_duration_s=3,
            resolution="1280x720",
        )
        JobDB.update_job_state(test_db_session, job.job_id, "RUNNING")

        response = await client.post(
            f"/v1/t2v/jobs/{job.job_id}/finalize",
            json={"selected_seeds": {"1": 12345}},
            headers=auth_headers
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "INVALID_JOB_STATE"


class TestReviseAPI:
    """E2E tests for /v1/t2v/jobs/{job_id}/revise endpoint"""

    @pytest_asyncio.fixture
    async def client(self, test_db_session):
        """Create test client"""
        from src.api.main import app
        from src.models import get_db

        async def override_get_db():
            yield test_db_session

        app.dependency_overrides[get_db] = override_get_db
        await app.router.startup()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
        await app.router.shutdown()
        app.dependency_overrides.clear()

    @pytest.fixture
    def auth_headers(self):
        """Mock authentication headers"""
        return {"X-API-Key": "test-key"}

    async def test_revise_job(
        self,
        client: httpx.AsyncClient,
        auth_headers,
        test_db_session,
    ):
        """Test revising a job"""
        # Create a completed job
        from src.services.storage import JobDB

        job = JobDB.create_job(
            db=test_db_session,
            user_input_redacted="测试视频",
            user_input_hash="abc123",
            template_id="test_template",
            template_version="1.0",
            quality_mode="balanced",
            ir={"topic": "失眠", "intent": "mood_video"},
            shot_plan={"template_id": "test_template", "shots": []},
            shot_requests=[],
            external_task_ids=[],
            total_duration_s=3,
            resolution="1280x720",
        )
        job.state = "SUCCEEDED"
        test_db_session.commit()

        request_data = {
            "feedback": "镜头太晃动了，希望稳定一些"
        }

        # Mock job manager
        with patch('src.api.routes.revise.JobManager') as mock_job_manager:
            mock_job = Mock(job_id="revision_job_123", state="CREATED")
            mock_job_manager.return_value.execute_revision_workflow = AsyncMock(
                return_value=mock_job
            )

            response = await client.post(
                f"/v1/t2v/jobs/{job.job_id}/revise",
                json=request_data,
                headers=auth_headers
            )

            assert response.status_code == 202
            data = response.json()
            assert "job_id" in data

    async def test_revise_invalid_state(
        self,
        client: httpx.AsyncClient,
        auth_headers,
        test_db_session,
    ):
        """Revise should fail if job is not succeeded."""
        from src.services.storage import JobDB

        job = JobDB.create_job(
            db=test_db_session,
            user_input_redacted="test",
            user_input_hash="hash",
            template_id="template",
            template_version="1.0",
            quality_mode="balanced",
            ir={"topic": "insomnia", "intent": "mood_video"},
            shot_plan={},
            shot_requests=[],
            external_task_ids=[],
            total_duration_s=3,
            resolution="1280x720",
        )
        JobDB.update_job_state(test_db_session, job.job_id, "RUNNING")

        response = await client.post(
            f"/v1/t2v/jobs/{job.job_id}/revise",
            json={"feedback": "reduce camera shake"},
            headers=auth_headers
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "INVALID_JOB_STATE"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
