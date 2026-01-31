"""
Unit Tests for FFmpegSplitter
"""

import os
import subprocess
import pytest

from src.services.ffmpeg_splitter import FFmpegSplitter, FFmpegError


def _completed(returncode=0, stderr=b""):
    return subprocess.CompletedProcess(
        args=["ffmpeg"],
        returncode=returncode,
        stdout=b"",
        stderr=stderr,
    )


def test_split_video_audio_missing_input(tmp_path):
    """Missing input should raise FFmpegError."""
    splitter = FFmpegSplitter()
    missing = tmp_path / "missing.mp4"

    with pytest.raises(FFmpegError) as exc_info:
        splitter.split_video_audio(
            str(missing),
            str(tmp_path / "video.mp4"),
            str(tmp_path / "audio.mp3"),
        )

    assert exc_info.value.code == splitter.ERROR_INPUT_FILE_NOT_FOUND


def test_split_video_audio_video_failure(tmp_path, monkeypatch):
    """Video extraction failure should raise FFmpegError."""
    splitter = FFmpegSplitter()
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"data")

    monkeypatch.setattr(
        splitter,
        "_extract_video",
        lambda *_args, **_kwargs: _completed(returncode=1, stderr=b"bad video"),
    )

    with pytest.raises(FFmpegError) as exc_info:
        splitter.split_video_audio(
            str(input_path),
            str(tmp_path / "video.mp4"),
            str(tmp_path / "audio.mp3"),
        )

    assert exc_info.value.code == splitter.ERROR_EXTRACTION_FAILED


def test_split_video_audio_audio_failure(tmp_path, monkeypatch):
    """Audio extraction failure should raise FFmpegError."""
    splitter = FFmpegSplitter()
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"data")
    video_path = tmp_path / "video.mp4"

    def _extract_video(_input, output):
        with open(output, "wb") as f:
            f.write(b"video")
        return _completed(returncode=0)

    monkeypatch.setattr(splitter, "_extract_video", _extract_video)
    monkeypatch.setattr(
        splitter,
        "_extract_audio",
        lambda *_args, **_kwargs: _completed(returncode=1, stderr=b"bad audio"),
    )

    with pytest.raises(FFmpegError) as exc_info:
        splitter.split_video_audio(
            str(input_path),
            str(video_path),
            str(tmp_path / "audio.mp3"),
        )

    assert exc_info.value.code == splitter.ERROR_EXTRACTION_FAILED


def test_split_video_audio_success(tmp_path, monkeypatch):
    """Successful split returns metadata and writes files."""
    splitter = FFmpegSplitter()
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"data")
    video_path = tmp_path / "video.mp4"
    audio_path = tmp_path / "audio.mp3"

    def _extract_video(_input, output):
        with open(output, "wb") as f:
            f.write(b"video")
        return _completed(returncode=0)

    def _extract_audio(_input, output):
        with open(output, "wb") as f:
            f.write(b"audio")
        return _completed(returncode=0)

    monkeypatch.setattr(splitter, "_extract_video", _extract_video)
    monkeypatch.setattr(splitter, "_extract_audio", _extract_audio)
    monkeypatch.setattr(splitter, "_get_video_duration", lambda _path: 4.5)

    result = splitter.split_video_audio(str(input_path), str(video_path), str(audio_path))

    assert result["success"] is True
    assert result["duration_s"] == 4.5
    assert os.path.exists(video_path)
    assert os.path.exists(audio_path)
