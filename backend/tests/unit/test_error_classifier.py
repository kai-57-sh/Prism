"""
Unit Tests for ErrorClassifier
"""

import httpx

from src.services.error_classifier import ErrorClassifier
from src.services.ffmpeg_splitter import FFmpegError


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(status_code, request=request, text="error")
    return httpx.HTTPStatusError("error", request=request, response=response)


def test_classify_timeout():
    classifier = ErrorClassifier()
    error = httpx.ReadTimeout("timeout", request=httpx.Request("GET", "https://example.com"))

    result = classifier.classify(error)

    assert result["code"] == classifier.ERROR_NETWORK_TIMEOUT
    assert result["retryable"] is True


def test_classify_network_error():
    classifier = ErrorClassifier()
    error = httpx.NetworkError("network", request=httpx.Request("GET", "https://example.com"))

    result = classifier.classify(error)

    assert result["code"] == classifier.ERROR_NETWORK_ERROR
    assert result["retryable"] is True


def test_classify_http_status_errors():
    classifier = ErrorClassifier()

    result_401 = classifier.classify(_http_status_error(401))
    assert result_401["code"] == classifier.ERROR_DASHSCOPE_AUTH
    assert result_401["retryable"] is False

    result_429 = classifier.classify(_http_status_error(429))
    assert result_429["code"] == classifier.ERROR_DASHSCOPE_RATE_LIMIT
    assert result_429["retryable"] is True

    result_400 = classifier.classify(_http_status_error(400))
    assert result_400["code"] == classifier.ERROR_DASHSCOPE_INVALID_PARAM
    assert result_400["retryable"] is False

    result_500 = classifier.classify(_http_status_error(500))
    assert result_500["code"] == classifier.ERROR_DASHSCOPE_TIMEOUT
    assert result_500["retryable"] is True


def test_classify_ffmpeg_error():
    classifier = ErrorClassifier()
    error = FFmpegError("missing", "INPUT_FILE_NOT_FOUND")

    result = classifier.classify(error)

    assert result["code"] == "INPUT_FILE_NOT_FOUND"
    assert result["retryable"] is False


def test_classify_validation_error():
    classifier = ErrorClassifier()
    error = ValueError("duration invalid")

    result = classifier.classify(error)

    assert result["code"] == classifier.ERROR_VALIDATION_FAILED
    assert any("duration" in suggestion.lower() for suggestion in result["suggested_modifications"])


def test_classify_unknown_error():
    classifier = ErrorClassifier()
    result = classifier.classify(Exception("boom"))

    assert result["code"] == classifier.ERROR_UNKNOWN
    assert result["retryable"] is False
