"""
Integration Tests for Storage Services
"""

import pytest
from src.services.storage import JobDB, TemplateDB
from src.models.job import JobModel, JobState
from src.models.template import TemplateModel


class TestJobDB:
    """Integration tests for Job database operations"""

    @pytest.fixture
    def sample_job(self):
        """Create sample job"""
        return JobModel(
            job_id="test_job_123",
            user_input_redacted="我想要一个关于失眠的视频",
            input_hash="abc123def456",
            ir={
                "topic": "失眠",
                "intent": "mood_video",
                "style": {"visual": "舒缓"}
            },
            shot_plan={
                "template_id": "insomnia_relaxation",
                "shots": []
            },
            shot_requests=[],
            shot_assets=[],
            state=JobState.CREATED,
            quality_mode="balanced",
            resolution="1280*720"
        )

    def test_create_job(self, test_db_session: "Session", sample_job: JobModel):
        """Test creating a job in database"""
        JobDB.create_job(test_db_session, sample_job)

        # Retrieve job
        retrieved = JobDB.get_job(test_db_session, "test_job_123")

        assert retrieved is not None
        assert retrieved.job_id == "test_job_123"
        assert retrieved.user_input_redacted == sample_job.user_input_redacted
        assert retrieved.state == JobState.CREATED

    def test_update_job_state(self, test_db_session: "Session", sample_job: JobModel):
        """Test updating job state"""
        JobDB.create_job(test_db_session, sample_job)

        # Update state
        JobDB.update_job_state(
            test_db_session,
            "test_job_123",
            JobState.RUNNING
        )

        # Verify update
        retrieved = JobDB.get_job(test_db_session, "test_job_123")
        assert retrieved.state == JobState.RUNNING

    def test_update_job_with_shot_plan(self, test_db_session: "Session", sample_job: JobModel):
        """Test updating job with shot plan"""
        JobDB.create_job(test_db_session, sample_job)

        shot_plan = {
            "template_id": "test_template",
            "shots": [
                {"shot_id": 1, "duration_s": 3},
                {"shot_id": 2, "duration_s": 4}
            ]
        }

        JobDB.update_job_shot_plan(test_db_session, "test_job_123", shot_plan)

        retrieved = JobDB.get_job(test_db_session, "test_job_123")
        assert retrieved.shot_plan == shot_plan

    def test_update_job_with_assets(self, test_db_session: "Session", sample_job: JobModel):
        """Test updating job with shot assets"""
        JobDB.create_job(test_db_session, sample_job)

        assets = [
            {
                "shot_id": 1,
                "video_url": "https://example.com/video1.mp4",
                "audio_url": "https://example.com/audio1.mp3",
                "duration_s": 3,
                "resolution": "1280*720"
            }
        ]

        JobDB.update_job_shot_assets(test_db_session, "test_job_123", assets)

        retrieved = JobDB.get_job(test_db_session, "test_job_123")
        assert len(retrieved.shot_assets) == 1
        assert retrieved.shot_assets[0]["video_url"] == assets[0]["video_url"]

    def test_list_jobs(self, test_db_session: "Session"):
        """Test listing all jobs"""
        # Create multiple jobs
        for i in range(3):
            job = JobModel(
                job_id=f"job_{i}",
                user_input_redacted=f"测试输入 {i}",
                input_hash=f"hash_{i}",
                state=JobState.CREATED
            )
            JobDB.create_job(test_db_session, job)

        # List jobs
        jobs = JobDB.list_jobs(test_db_session)

        assert len(jobs) >= 3

    def test_get_jobs_by_state(self, test_db_session: "Session"):
        """Test filtering jobs by state"""
        # Create jobs with different states
        job1 = JobModel(
            job_id="job_1",
            user_input_redacted="测试",
            input_hash="hash_1",
            state=JobState.CREATED
        )
        job2 = JobModel(
            job_id="job_2",
            user_input_redacted="测试",
            input_hash="hash_2",
            state=JobState.RUNNING
        )

        JobDB.create_job(test_db_session, job1)
        JobDB.create_job(test_db_session, job2)

        # Get jobs by state
        created_jobs = JobDB.get_jobs_by_state(test_db_session, JobState.CREATED)
        running_jobs = JobDB.get_jobs_by_state(test_db_session, JobState.RUNNING)

        assert len(created_jobs) >= 1
        assert len(running_jobs) >= 1

    def test_delete_job(self, test_db_session: "Session", sample_job: JobModel):
        """Test deleting a job"""
        JobDB.create_job(test_db_session, sample_job)

        # Delete job
        JobDB.delete_job(test_db_session, "test_job_123")

        # Verify deletion
        retrieved = JobDB.get_job(test_db_session, "test_job_123")
        assert retrieved is None


class TestTemplateDB:
    """Integration tests for Template database operations"""

    @pytest.fixture
    def sample_template(self):
        """Create sample template"""
        return TemplateModel(
            template_id="insomnia_relaxation",
            version="1.0",
            shot_skeletons=[
                {
                    "shot_id": 1,
                    "duration_s": 3,
                    "camera": "固定镜头",
                    "visual_template": "宁静场景",
                    "audio_template": "轻柔音乐",
                    "subtitle_policy": "none"
                }
            ],
            constraints={
                "max_duration_s": 15,
                "min_duration_s": 5,
                "watermark_default": False
            },
            tags={
                "topic": ["失眠", "焦虑"],
                "tone": ["舒缓", "治愈"],
                "style": ["写实", "温暖"]
            }
        )

    def test_create_template(self, test_db_session: "Session", sample_template: TemplateModel):
        """Test creating a template in database"""
        TemplateDB.create_template(test_db_session, sample_template)

        # Retrieve template
        retrieved = TemplateDB.get_template(
            test_db_session,
            "insomnia_relaxation",
            "1.0"
        )

        assert retrieved is not None
        assert retrieved.template_id == "insomnia_relaxation"
        assert retrieved.version == "1.0"

    def test_list_templates(self, test_db_session: "Session"):
        """Test listing all templates"""
        # Create multiple templates
        for i in range(3):
            template = TemplateModel(
                template_id=f"template_{i}",
                version="1.0",
                shot_skeletons=[],
                constraints={},
                tags={}
            )
            TemplateDB.create_template(test_db_session, template)

        # List templates
        templates = TemplateDB.list_templates(test_db_session)

        assert len(templates) >= 3

    def test_get_template_not_found(self, test_db_session: "Session"):
        """Test getting non-existent template"""
        template = TemplateDB.get_template(
            test_db_session,
            "nonexistent",
            "1.0"
        )

        assert template is None

    def test_delete_template(self, test_db_session: "Session", sample_template: TemplateModel):
        """Test deleting a template"""
        TemplateDB.create_template(test_db_session, sample_template)

        # Delete template
        TemplateDB.delete_template(
            test_db_session,
            "insomnia_relaxation",
            "1.0"
        )

        # Verify deletion
        retrieved = TemplateDB.get_template(
            test_db_session,
            "insomnia_relaxation",
            "1.0"
        )
        assert retrieved is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
