"""
Unit Tests for AssetStorage
"""

import os
import pytest

from src.config.settings import settings
from src.services.asset_storage import AssetStorage


@pytest.fixture
def storage(tmp_path, monkeypatch):
    """Create AssetStorage using a temporary static root."""
    monkeypatch.setattr(settings, "static_root", str(tmp_path))
    monkeypatch.setattr(settings, "static_video_subdir", "vedios")
    monkeypatch.setattr(settings, "static_video_dir", str(tmp_path / "vedios"))
    monkeypatch.setattr(settings, "static_audio_dir", str(tmp_path / "audio"))
    monkeypatch.setattr(settings, "static_metadata_dir", str(tmp_path / "metadata"))
    return AssetStorage()


def test_paths_and_urls(storage: AssetStorage):
    """Test path and URL generation."""
    video_path = storage.get_video_storage_path("job1", 2)
    audio_path = storage.get_audio_storage_path("job1", 2)
    metadata_path = storage.get_metadata_storage_path("job1")

    assert video_path.endswith(".mp4")
    assert "job1_shot_2" in video_path
    assert audio_path.endswith(".mp3")
    assert "job1_shot_2" in audio_path
    assert metadata_path.endswith("job1.json")

    video_url = storage.get_video_url("job1", 2)
    audio_url = storage.get_audio_url("job1", 2)
    metadata_url = storage.get_metadata_url("job1")

    assert video_url.startswith(settings.static_url_prefix)
    assert "/vedios/" in video_url
    assert audio_url.startswith(settings.static_url_prefix)
    assert "/audio/" in audio_url
    assert metadata_url == f"{settings.static_url_prefix}/metadata/job1.json"


def test_write_and_read_metadata(storage: AssetStorage):
    """Test metadata round-trip."""
    metadata = {"job_id": "job1", "status": "ok"}

    path = storage.write_job_metadata("job1", metadata)
    assert os.path.exists(path)

    loaded = storage.read_job_metadata("job1")
    assert loaded["job_id"] == "job1"
    assert loaded["status"] == "ok"


def test_delete_job_assets(storage: AssetStorage):
    """Test deleting video/audio/metadata assets."""
    video_path = storage.get_video_storage_path("job1", 1)
    audio_path = storage.get_audio_storage_path("job1", 1)
    metadata_path = storage.write_job_metadata("job1", {"job_id": "job1"})

    for path in [video_path, audio_path]:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(b"data")

    deleted = storage.delete_job_assets("job1")

    assert video_path in deleted
    assert audio_path in deleted
    assert metadata_path in deleted
    assert not os.path.exists(video_path)
    assert not os.path.exists(audio_path)
    assert not os.path.exists(metadata_path)
