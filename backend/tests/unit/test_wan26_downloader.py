"""
Unit Tests for Wan26Downloader
"""

import os
import httpx
import pytest

from src.services.wan26_downloader import Wan26Downloader


class _MockStreamResponse:
    def __init__(self, chunks, status_code=200):
        self._chunks = chunks
        self.status_code = status_code
        self.request = httpx.Request("GET", "https://example.com/video.mp4")

    def raise_for_status(self):
        if self.status_code >= 400:
            response = httpx.Response(self.status_code, request=self.request)
            raise httpx.HTTPStatusError("error", request=self.request, response=response)

    async def aiter_bytes(self, chunk_size=8192):
        for chunk in self._chunks:
            yield chunk


class _MockStreamContext:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _MockClient:
    def __init__(self, response):
        self._response = response

    def stream(self, _method, _url):
        return _MockStreamContext(self._response)


@pytest.mark.asyncio
async def test_download_video_success(tmp_path):
    """Test successful download writes file."""
    response = _MockStreamResponse([b"hello", b"world"], status_code=200)
    downloader = Wan26Downloader()
    downloader.client = _MockClient(response)

    target_path = tmp_path / "video.mp4"
    path = await downloader.download_video("https://example.com/video.mp4", str(target_path))

    assert path == str(target_path)
    assert os.path.exists(path)
    assert os.path.getsize(path) > 0


@pytest.mark.asyncio
async def test_download_video_http_error(tmp_path):
    """Test HTTP error propagates."""
    response = _MockStreamResponse([b""], status_code=404)
    downloader = Wan26Downloader()
    downloader.client = _MockClient(response)

    with pytest.raises(httpx.HTTPStatusError):
        await downloader.download_video("https://example.com/video.mp4", str(tmp_path / "video.mp4"))
