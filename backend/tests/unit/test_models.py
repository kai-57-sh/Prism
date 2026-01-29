"""
Unit Tests for Data Models
"""

import pytest
from src.models.job import JobModel, JobState
from src.models.ir import IR
from src.models.shot_plan import ShotPlan
from src.models.shot_asset import ShotAsset
from src.models.shot_request import ShotRequest
from src.models.template import TemplateModel


class TestJobModel:
    """Test suite for JobModel"""

    def test_create_job_model(self):
        """Test creating a job model"""
        job = JobModel(
            job_id="test_job_123",
            user_input_redacted="测试输入",
            input_hash="abc123",
            state=JobState.CREATED,
            quality_mode="balanced",
            resolution="1280*720"
        )

        assert job.job_id == "test_job_123"
        assert job.user_input_redacted == "测试输入"
        assert job.state == JobState.CREATED
        assert job.quality_mode == "balanced"

    def test_job_state_transitions(self):
        """Test job state transitions"""
        job = JobModel(
            job_id="test_job_123",
            user_input_redacted="测试",
            input_hash="abc123",
            state=JobState.CREATED
        )

        # CREATED -> SUBMITTED
        job.state = JobState.SUBMITTED
        assert job.state == JobState.SUBMITTED

        # SUBMITTED -> RUNNING
        job.state = JobState.RUNNING
        assert job.state == JobState.RUNNING

        # RUNNING -> SUCCEEDED
        job.state = JobState.SUCCEEDED
        assert job.state == JobState.SUCCEEDED

    def test_job_model_with_ir(self):
        """Test job model with IR"""
        ir_data = {
            "topic": "失眠",
            "intent": "mood_video",
            "style": {"visual": "舒缓"}
        }

        job = JobModel(
            job_id="test_job_123",
            user_input_redacted="测试",
            input_hash="abc123",
            ir=ir_data,
            state=JobState.CREATED
        )

        assert job.ir == ir_data
        assert job.ir["topic"] == "失眠"

    def test_job_model_with_shot_plan(self):
        """Test job model with shot plan"""
        shot_plan_data = {
            "template_id": "test_template",
            "shots": [
                {"shot_id": 1, "duration_s": 3},
                {"shot_id": 2, "duration_s": 4}
            ]
        }

        job = JobModel(
            job_id="test_job_123",
            user_input_redacted="测试",
            input_hash="abc123",
            shot_plan=shot_plan_data,
            state=JobState.CREATED
        )

        assert job.shot_plan == shot_plan_data
        assert len(job.shot_plan["shots"]) == 2

    def test_job_model_revision(self):
        """Test revision job"""
        parent_job_id = "parent_job_123"

        job = JobModel(
            job_id="revision_job_456",
            user_input_redacted="修改意见",
            input_hash="def456",
            revision_of=parent_job_id,
            state=JobState.CREATED
        )

        assert job.revision_of == parent_job_id


class TestIR:
    """Test suite for IR model"""

    def test_create_ir(self):
        """Test creating IR"""
        ir = IR(
            topic="失眠",
            intent="mood_video",
            style={"visual": "舒缓"},
            scene={"location": "卧室"},
            characters=[],
            emotion_curve=["焦虑", "平静"],
            subtitle_policy="none",
            audio={"mode": "tts"},
            duration_preference_s=10,
            quality_mode="balanced"
        )

        assert ir.topic == "失眠"
        assert ir.intent == "mood_video"
        assert ir.duration_preference_s == 10


class TestShotPlan:
    """Test suite for ShotPlan model"""

    def test_create_shot_plan(self):
        """Test creating shot plan"""
        shots = [
            {
                "shot_id": 1,
                "duration_s": 3,
                "compiled_prompt": "测试提示词"
            }
        ]

        shot_plan = ShotPlan(
            template_id="test_template",
            template_version="1.0",
            duration_s=10,
            subtitle_policy="none",
            shots=shots,
            global_style={"visual": "舒缓"}
        )

        assert shot_plan.template_id == "test_template"
        assert shot_plan.duration_s == 10
        assert len(shot_plan.shots) == 1


class TestShotAsset:
    """Test suite for ShotAsset model"""

    def test_create_shot_asset(self):
        """Test creating shot asset"""
        asset = ShotAsset(
            shot_id=1,
            video_url="https://example.com/video.mp4",
            audio_url="https://example.com/audio.mp3",
            duration_s=3,
            resolution="1280*720"
        )

        assert asset.shot_id == 1
        assert asset.video_url
        assert asset.audio_url
        assert asset.duration_s == 3


class TestShotRequest:
    """Test suite for ShotRequest model"""

    def test_create_shot_request(self):
        """Test creating shot request"""
        request = ShotRequest(
            shot_id=1,
            compiled_prompt="测试提示词",
            compiled_negative_prompt="负面提示词",
            params={
                "size": "1280*720",
                "duration": 3,
                "seed": 12345
            }
        )

        assert request.shot_id == 1
        assert request.compiled_prompt == "测试提示词"
        assert request.params["size"] == "1280*720"


class TestTemplateModel:
    """Test suite for TemplateModel"""

    def test_create_template(self):
        """Test creating template"""
        template = TemplateModel(
            template_id="test_template",
            version="1.0",
            shot_skeletons=[
                {
                    "shot_id": 1,
                    "duration_s": 3,
                    "camera": "固定镜头"
                }
            ],
            constraints={
                "max_duration_s": 15,
                "min_duration_s": 5
            },
            tags={
                "topic": ["失眠"],
                "tone": ["舒缓"]
            }
        )

        assert template.template_id == "test_template"
        assert template.version == "1.0"
        assert len(template.shot_skeletons) == 1

    def test_template_to_dict(self):
        """Test template serialization to dict"""
        template = TemplateModel(
            template_id="test_template",
            version="1.0",
            shot_skeletons=[],
            constraints={},
            tags={}
        )

        data = template.to_dict()

        assert data["template_id"] == "test_template"
        assert data["version"] == "1.0"
        assert "shot_skeletons" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
