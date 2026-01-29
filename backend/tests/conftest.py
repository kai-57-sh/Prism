"""
Pytest Configuration and Fixtures
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from unittest.mock import Mock, AsyncMock, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.config.settings import settings
from src.models.job import JobModel, Base


@pytest.fixture
def test_db_path() -> Generator[str, None, None]:
    """Create temporary database file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def test_db_engine(test_db_path: str) -> Generator:
    """Create test database engine"""
    engine = create_engine(f"sqlite:///{test_db_path}")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def test_db_session(test_db_engine) -> Generator[Session, None, None]:
    """Create test database session"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for file operations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_qwen_llm():
    """Mock Qwen LLM"""
    mock = Mock()
    mock.invoke = Mock(return_value=Mock(
        content='{"topic": "测试主题", "intent": "测试意图"}'
    ))
    return mock


@pytest.fixture
def mock_dashscope_client():
    """Mock DashScope VideoSynthesis client"""
    mock = Mock()

    # Mock async_call response
    mock_async_call = Mock()
    mock_async_call.status_code = 200
    mock_async_call.output = Mock(task_id="test_task_123")
    mock.async_call = Mock(return_value=mock_async_call)

    # Mock wait response
    mock_wait = Mock()
    mock_wait.status_code = 200
    mock_wait.output = Mock(
        video_url="https://example.com/video.mp4"
    )
    mock.wait = Mock(return_value=mock_wait)

    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    mock = Mock()
    mock.get = Mock(return_value=None)
    mock.set = Mock(return_value=True)
    mock.incr = Mock(return_value=1)
    mock.expire = Mock(return_value=True)
    mock.delete = Mock(return_value=True)
    return mock


@pytest.fixture
def sample_ir():
    """Sample Intermediate Representation"""
    return {
        "topic": "失眠",
        "intent": "mood_video",
        "style": {
            "visual": "舒缓风格",
            "color_tone": "暖色调",
            "lighting": "柔和光线"
        },
        "scene": {
            "location": "卧室",
            "time": "夜晚"
        },
        "characters": [],
        "emotion_curve": ["焦虑", "平静", "安详"],
        "subtitle_policy": "none",
        "audio": {
            "mode": "tts",
            "narration_language": "zh-CN",
            "narration_tone": "舒缓",
            "sfx": ["轻柔音乐", "环境音"]
        },
        "duration_preference_s": 10,
        "quality_mode": "balanced"
    }


@pytest.fixture
def sample_template():
    """Sample medical scene template"""
    return {
        "template_id": "insomnia_relaxation",
        "version": "1.0",
        "shot_skeletons": [
            {
                "shot_id": 1,
                "duration_s": 3,
                "camera": "固定镜头",
                "visual_template": "宁静的卧室场景",
                "audio_template": "轻柔背景音乐",
                "subtitle_policy": "none"
            },
            {
                "shot_id": 2,
                "duration_s": 4,
                "camera": "缓慢推进",
                "visual_template": "人物逐渐放松",
                "audio_template": "舒缓旁白",
                "subtitle_policy": "allowed"
            },
            {
                "shot_id": 3,
                "duration_s": 3,
                "camera": "缓慢拉远",
                "visual_template": "安详入睡",
                "audio_template": "音乐渐弱",
                "subtitle_policy": "none"
            }
        ],
        "constraints": {
            "max_duration_s": 15,
            "min_duration_s": 5,
            "watermark_default": False
        },
        "tags": {
            "topic": ["失眠", "焦虑"],
            "tone": ["舒缓", "治愈"],
            "style": ["写实", "温暖"]
        }
    }


@pytest.fixture
def sample_shot_plan():
    """Sample shot plan"""
    return {
        "template_id": "insomnia_relaxation",
        "template_version": "1.0",
        "duration_s": 10,
        "subtitle_policy": "none",
        "shots": [
            {
                "shot_id": 1,
                "duration_s": 3,
                "camera": "固定镜头",
                "compiled_prompt": "宁静的卧室，月光透过窗户洒在床上",
                "compiled_negative_prompt": "",
                "audio": {
                    "mode": "tts",
                    "narration": "深呼吸，放松身体",
                    "sfx": ["轻柔音乐"]
                },
                "seed": 12345
            },
            {
                "shot_id": 2,
                "duration_s": 4,
                "camera": "缓慢推进",
                "compiled_prompt": "人物躺在床上，表情逐渐放松",
                "compiled_negative_prompt": "",
                "audio": {
                    "mode": "tts",
                    "narration": "让思绪慢慢平静",
                    "sfx": ["环境音"]
                },
                "seed": 12346
            },
            {
                "shot_id": 3,
                "duration_s": 3,
                "camera": "缓慢拉远",
                "compiled_prompt": "安详入睡的画面",
                "compiled_negative_prompt": "",
                "audio": {
                    "mode": "tts",
                    "narration": "晚安",
                    "sfx": []
                },
                "seed": 12347
            }
        ],
        "global_style": {
            "visual": "舒缓风格",
            "color_tone": "暖色调",
            "lighting": "柔和光线"
        }
    }


@pytest.fixture
def sample_job():
    """Sample job model"""
    return JobModel(
        job_id="test_job_123",
        user_input_redacted="我想要一个关于失眠的视频",
        input_hash="abc123",
        ir={
            "topic": "失眠",
            "intent": "mood_video"
        },
        shot_plan={},
        shot_requests=[],
        shot_assets=[],
        state="CREATED",
        quality_mode="balanced",
        resolution="1280*720"
    )


# Test configurations
@pytest.fixture
def test_settings():
    """Test configuration overrides"""
    return {
        "database_url": "sqlite:///./test.db",
        "redis_url": "redis://localhost:6379/1",
        "log_level": "DEBUG"
    }


# Async fixtures
@pytest.fixture
async def async_mock_client():
    """Async mock HTTP client"""
    mock = AsyncMock()
    mock.post = AsyncMock(return_value=Mock(
        status_code=200,
        json=Mock(return_value={"output": {"task_id": "test_task_123"}})
    ))
    mock.get = AsyncMock(return_value=Mock(
        status_code=200,
        json=Mock(return_value={
            "output": {
                "task_status": "SUCCEEDED",
                "results": [{"url": "https://example.com/video.mp4"}]
            }
        })
    ))
    return mock


# Environment fixtures
@pytest.fixture
def mock_env_vars():
    """Mock environment variables"""
    os.environ["DASHSCOPE_API_KEY"] = "test-dashscope-key"
    os.environ["MODELSCOPE_API_KEY"] = "ms-test-modelscope-key"
    os.environ["MODELSCOPE_BASE_URL"] = "https://test-api.modelscope.cn/v1"
    os.environ["QWEN_MODEL"] = "Qwen/Qwen3-235B-A22B-Instruct-2507"

    yield

    # Cleanup
    for key in ["DASHSCOPE_API_KEY", "MODELSCOPE_API_KEY", "MODELSCOPE_BASE_URL", "QWEN_MODEL"]:
        if key in os.environ:
            del os.environ[key]
