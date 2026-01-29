"""
Workflow Integration Tests
"""

import pytest
from unittest.mock import AsyncMock, Mock


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


def _stub_generation_dependencies(job_manager, ir, template, shot_plan, assets):
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
    job_manager.validator.validate_parameters = Mock(return_value=(True, None))
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
    job_manager._generate_shots = AsyncMock(return_value=assets)
    job_manager._write_job_metadata = Mock()


class TestGenerationWorkflow:
    """Integration tests for complete generation workflow"""

    @pytest.mark.asyncio
    async def test_generation_workflow_simple(self, job_manager: "JobManager", test_db_session):
        """Test simple generation workflow"""
        from src.core.llm_orchestrator import IR
        from src.services.storage import JobDB

        user_prompt = "I want a calming insomnia video"

        ir = IR(
            topic="insomnia",
            intent="mood_video",
            style={"visual": "calm", "color_tone": "warm", "lighting": "soft"},
            scene={"location": "bedroom", "time": "night"},
            characters=[],
            emotion_curve=["calm"],
            subtitle_policy="none",
            audio={"mode": "tts", "narration_language": "zh-CN", "narration_tone": "calm"},
            duration_preference_s=6,
            quality_mode="fast",
        )

        template = {
            "template_id": "test_template",
            "version": "1.0",
            "negative_prompt_base": "",
            "shot_skeletons": [
                {
                    "shot_id": 1,
                    "duration_s": 3,
                    "camera": "static",
                    "visual_template": "scene",
                    "audio_template": "audio",
                    "subtitle_policy": "none",
                }
            ],
            "constraints": {},
            "tags": {},
        }
        shot_plan = {
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
        assets = [
            {
                "shot_id": 1,
                "seed": 12345,
                "video_url": "https://example.com/video.mp4",
                "audio_url": "https://example.com/audio.mp3",
                "duration_s": 3,
                "resolution": "1280x720",
            }
        ]

        _stub_generation_dependencies(job_manager, ir, template, shot_plan, assets)

        job = await job_manager.execute_generation_workflow(
            db=test_db_session,
            user_input=user_prompt,
            quality_mode="fast",
            client_ip="192.168.1.1",
            resolution="1280x720",
        )

        assert job.job_id

        stored = JobDB.get_job(test_db_session, job.job_id)
        assert stored is not None
        assert stored.state == "SUCCEEDED"

    @pytest.mark.asyncio
    async def test_generation_workflow_with_quality_modes(self, job_manager: "JobManager", test_db_session):
        """Test generation workflow with different quality modes"""
        from src.core.llm_orchestrator import IR

        user_prompt = "An anxiety themed video"
        quality_modes = ["fast", "balanced", "high"]

        template = {
            "template_id": "test_template",
            "version": "1.0",
            "negative_prompt_base": "",
            "shot_skeletons": [],
            "constraints": {},
            "tags": {},
        }
        shot_plan = {
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
        assets = [
            {
                "shot_id": 1,
                "seed": 12345,
                "video_url": "https://example.com/video.mp4",
                "audio_url": "https://example.com/audio.mp3",
                "duration_s": 3,
                "resolution": "1280x720",
            }
        ]

        for quality_mode in quality_modes:
            ir = IR(
                topic="anxiety",
                intent="mood_video",
                style={"visual": "calm", "color_tone": "warm", "lighting": "soft"},
                scene={"location": "room", "time": "night"},
                characters=[],
                emotion_curve=["calm"],
                subtitle_policy="none",
                audio={"mode": "tts", "narration_language": "en-US", "narration_tone": "calm"},
                duration_preference_s=6,
                quality_mode=quality_mode,
            )

            _stub_generation_dependencies(job_manager, ir, template, shot_plan, assets)

            job = await job_manager.execute_generation_workflow(
                db=test_db_session,
                user_input=user_prompt,
                quality_mode=quality_mode,
                client_ip="192.168.1.1",
                resolution="1280x720",
            )

            assert job.job_id


class TestFinalizationWorkflow:
    """Integration tests for finalization workflow"""

    @pytest.mark.asyncio
    async def test_finalization_workflow(self, job_manager: "JobManager", test_db_session):
        """Test finalization workflow"""
        from src.services.storage import JobDB

        parent_job = JobDB.create_job(
            db=test_db_session,
            user_input_redacted="test",
            user_input_hash="hash",
            template_id="test_template",
            template_version="1.0",
            quality_mode="fast",
            ir={},
            shot_plan={},
            shot_requests=[],
            external_task_ids=[],
            total_duration_s=3,
            resolution="1280x720",
        )

        JobDB.update_job_state(test_db_session, parent_job.job_id, "SUCCEEDED")

        job_manager._generate_final_shots = AsyncMock(
            return_value=[
                {
                    "shot_id": 1,
                    "seed": 12345,
                    "video_url": "https://example.com/video_hd.mp4",
                    "audio_url": "https://example.com/audio_hd.mp3",
                    "duration_s": 3,
                    "resolution": "1920x1080",
                }
            ]
        )
        job_manager._write_job_metadata = Mock()

        finalized = await job_manager.execute_finalization_workflow(
            db=test_db_session,
            job_id=parent_job.job_id,
            selected_seeds={1: 12345},
        )

        assert finalized.job_id == parent_job.job_id


class TestRevisionWorkflow:
    """Integration tests for revision workflow"""

    @pytest.mark.asyncio
    async def test_revision_workflow(self, job_manager: "JobManager", test_db_session):
        """Test revision workflow"""
        from src.services.storage import JobDB, TemplateDB
        from src.models.template import TemplateModel

        template = TemplateModel(
            template_id="test_template",
            version="1.0",
            tags={},
            constraints={},
            shot_skeletons=[
                {
                    "shot_id": 1,
                    "duration_s": 3,
                    "camera": "static",
                    "visual_template": "scene",
                    "audio_template": "audio",
                    "subtitle_policy": "none",
                }
            ],
            negative_prompt_base="",
        )
        TemplateDB.create_template(test_db_session, template)

        parent_job = JobDB.create_job(
            db=test_db_session,
            user_input_redacted="test",
            user_input_hash="hash",
            template_id="test_template",
            template_version="1.0",
            quality_mode="balanced",
            ir={
                "topic": "insomnia",
                "intent": "mood_video",
                "style": {"visual": "calm", "color_tone": "warm", "lighting": "soft"},
                "scene": {"location": "bedroom", "time": "night"},
                "characters": [],
                "emotion_curve": ["calm"],
                "subtitle_policy": "none",
                "audio": {"mode": "tts", "narration_language": "en-US", "narration_tone": "calm"},
                "duration_preference_s": 6,
                "quality_mode": "balanced",
            },
            shot_plan={},
            shot_requests=[],
            external_task_ids=[],
            total_duration_s=3,
            resolution="1280x720",
        )

        JobDB.update_job_state(test_db_session, parent_job.job_id, "SUCCEEDED")

        job_manager.llm_orchestrator.instantiate_template = Mock(
            return_value=Mock(
                dict=Mock(
                    return_value={
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
                )
            )
        )
        job_manager.validator.validate_parameters = Mock(return_value=(True, None))
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
        job_manager._generate_shots = AsyncMock(
            return_value=[
                {
                    "shot_id": 1,
                    "seed": 12345,
                    "video_url": "https://example.com/revised_video.mp4",
                    "audio_url": "https://example.com/revised_audio.mp3",
                    "duration_s": 3,
                    "resolution": "1280x720",
                }
            ]
        )
        job_manager._write_job_metadata = Mock()

        revision_job = await job_manager.execute_revision_workflow(
            db=test_db_session,
            parent_job_id=parent_job.job_id,
            feedback="reduce camera shake",
            targeted_fields=["camera"],
            suggested_modifications={"camera_motion": "stable"},
        )

        assert revision_job.revision_of == parent_job.job_id


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
