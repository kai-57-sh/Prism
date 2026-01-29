"""
Unit Tests for JobManager Failure Paths
"""

import pytest
from unittest.mock import AsyncMock, Mock

from src.services.storage import JobDB


@pytest.fixture
def job_manager(tmp_path, monkeypatch, mock_env_vars):
    """Create JobManager instance with temp static storage."""
    from src.config.settings import settings
    monkeypatch.setattr(settings, "static_root", str(tmp_path))
    monkeypatch.setattr(settings, "static_video_dir", str(tmp_path / "videos"))
    monkeypatch.setattr(settings, "static_audio_dir", str(tmp_path / "audio"))
    monkeypatch.setattr(settings, "static_metadata_dir", str(tmp_path / "metadata"))

    from src.services.job_manager import JobManager
    return JobManager()


def _base_ir(quality_mode="balanced"):
    from src.core.llm_orchestrator import IR
    return IR(
        topic="insomnia",
        intent="mood_video",
        style={"visual": "calm", "color_tone": "warm", "lighting": "soft"},
        scene={"location": "bedroom", "time": "night"},
        characters=[],
        emotion_curve=["calm"],
        subtitle_policy="none",
        audio={"mode": "tts", "narration_language": "zh-CN", "narration_tone": "calm"},
        duration_preference_s=6,
        quality_mode=quality_mode,
    )


def _template_dict():
    return {
        "template_id": "test_template",
        "version": "1.0",
        "negative_prompt_base": "",
        "shot_skeletons": [],
        "constraints": {},
        "tags": {},
    }


def _shot_plan_dict():
    return {
        "template_id": "test_template",
        "template_version": "1.0",
        "duration_s": 3,
        "subtitle_policy": "none",
        "shots": [
            {
                "shot_id": 1,
                "duration_s": 3,
                "visual": "scene",
                "camera_motion": "static",
                "audio": {"narration": "test", "sfx": "none"},
            }
        ],
        "global_style": {"style": "cinematic"},
    }


def _stub_base_pipeline(job_manager, ir, template, shot_plan):
    from src.core.template_router import TemplateMatch

    job_manager.rate_limiter.check_rate_limit = Mock(
        return_value={"allowed": True, "remaining": 1, "reset_at": 0}
    )
    job_manager.rate_limiter.check_concurrent_jobs = Mock(
        return_value={"allowed": True, "current": 0, "max": 5}
    )
    job_manager.rate_limiter.increment_concurrent_jobs = Mock()
    job_manager.rate_limiter.decrement_concurrent_jobs = Mock()

    job_manager.input_processor.process_input = Mock(
        return_value={
            "redacted_text": "test prompt",
            "input_hash": "hash",
            "pii_flags": [],
            "detected_language": "zh-CN",
            "translated_text": None,
        }
    )
    job_manager.llm_orchestrator.parse_ir = Mock(return_value=ir)
    job_manager.template_router.match_template = Mock(
        return_value=TemplateMatch(
            template_id=template["template_id"],
            version=template["version"],
            confidence=0.9,
            confidence_components={"cosine": 0.9, "jaccard": 0.9},
            template=template,
        )
    )
    job_manager.llm_orchestrator.instantiate_template = Mock(
        return_value=Mock(dict=Mock(return_value=shot_plan))
    )
    job_manager.prompt_compiler.compile_shot_prompt = Mock(
        return_value=Mock(
            compiled_prompt="prompt",
            compiled_negative_prompt="",
            params={
                "size": "1280*720",
                "duration": 3,
                "seed": 12345,
                "prompt_extend": False,
                "watermark": False,
            },
        )
    )
    job_manager._write_job_metadata = Mock()


@pytest.mark.asyncio
async def test_rate_limit_failure_no_job_created(job_manager, test_db_session):
    """Rate limit failures should not create jobs."""
    job_manager.rate_limiter.check_rate_limit = Mock(
        return_value={"allowed": False, "remaining": 0, "reset_at": 0}
    )

    with pytest.raises(ValueError):
        await job_manager.execute_generation_workflow(
            db=test_db_session,
            user_input="test",
            quality_mode="balanced",
            client_ip="192.168.1.1",
            resolution="1280x720",
        )

    assert JobDB.list_jobs(test_db_session) == []


@pytest.mark.asyncio
async def test_template_match_failure_no_job_created(job_manager, test_db_session):
    """Template match failures should not create jobs."""
    ir = _base_ir()
    _stub_base_pipeline(job_manager, ir, _template_dict(), _shot_plan_dict())
    job_manager.template_router.match_template = Mock(return_value=None)

    with pytest.raises(ValueError):
        await job_manager.execute_generation_workflow(
            db=test_db_session,
            user_input="test",
            quality_mode="balanced",
            client_ip="192.168.1.1",
            resolution="1280x720",
        )

    assert JobDB.list_jobs(test_db_session) == []


@pytest.mark.asyncio
async def test_validation_failure_no_job_created(job_manager, test_db_session):
    """Validation failures should not create jobs."""
    ir = _base_ir()
    _stub_base_pipeline(job_manager, ir, _template_dict(), _shot_plan_dict())
    job_manager.validator.validate_parameters = Mock(return_value=(False, ["bad"]))

    with pytest.raises(ValueError):
        await job_manager.execute_generation_workflow(
            db=test_db_session,
            user_input="test",
            quality_mode="balanced",
            client_ip="192.168.1.1",
            resolution="1280x720",
        )

    assert JobDB.list_jobs(test_db_session) == []


@pytest.mark.asyncio
async def test_external_failure_marks_job_failed(job_manager, test_db_session):
    """External failures should mark job as FAILED and store error details."""
    ir = _base_ir()
    _stub_base_pipeline(job_manager, ir, _template_dict(), _shot_plan_dict())
    job_manager.validator.validate_parameters = Mock(return_value=(True, None))
    job_manager._generate_shots = AsyncMock(side_effect=Exception("generation failed"))

    with pytest.raises(Exception):
        await job_manager.execute_generation_workflow(
            db=test_db_session,
            user_input="test",
            quality_mode="balanced",
            client_ip="192.168.1.1",
            resolution="1280x720",
        )

    jobs = JobDB.list_jobs(test_db_session)
    assert len(jobs) == 1
    job = jobs[0]
    assert job.state == "FAILED"
    assert job.error_details is not None
    assert job.state_transitions[-1]["state"] == "FAILED"
