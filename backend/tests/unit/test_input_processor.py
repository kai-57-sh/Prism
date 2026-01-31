"""
Unit Tests for Input Processor
"""

import pytest
from src.core.input_processor import InputProcessor


class TestInputProcessor:
    """Test suite for InputProcessor"""

    @pytest.fixture
    def processor(self):
        """Create InputProcessor instance"""
        return InputProcessor()

    def test_redact_email(self, processor: InputProcessor):
        """Test PII email redaction"""
        user_input = "我的邮箱是 test@example.com，请联系我"
        redacted, input_hash, pii_flags = processor.redact_user_input(user_input)

        assert "test@example.com" not in redacted
        assert "[EMAIL_REDACTED]" in redacted
        assert "email" in pii_flags
        assert input_hash
        assert len(input_hash) == 64  # SHA256 hash length

    def test_redact_phone(self, processor: InputProcessor):
        """Test PII phone redaction"""
        user_input = "我的电话是 123-456-7890"
        redacted, input_hash, pii_flags = processor.redact_user_input(user_input)

        assert "123-456-7890" not in redacted
        assert "[PHONE_REDACTED]" in redacted
        assert "phone" in pii_flags

    def test_redact_ssn(self, processor: InputProcessor):
        """Test PII SSN redaction"""
        user_input = "我的社保号是 123-45-6789"
        redacted, input_hash, pii_flags = processor.redact_user_input(user_input)

        assert "123-45-6789" not in redacted
        assert "[SSN_REDACTED]" in redacted
        assert "ssn" in pii_flags

    def test_redact_credit_card(self, processor: InputProcessor):
        """Test PII credit card redaction"""
        user_input = "信用卡号是 4532-1234-5678-9010"
        redacted, input_hash, pii_flags = processor.redact_user_input(user_input)

        assert "4532-1234-5678-9010" not in redacted
        assert "[CREDIT_CARD_REDACTED]" in redacted
        assert "credit_card" in pii_flags

    def test_redact_ip_address(self, processor: InputProcessor):
        """Test PII IP address redaction"""
        user_input = "我的 IP 是 192.168.1.1"
        redacted, input_hash, pii_flags = processor.redact_user_input(user_input)

        assert "192.168.1.1" not in redacted
        assert "[IP_ADDRESS_REDACTED]" in redacted
        assert "ip_address" in pii_flags

    def test_redact_multiple_pii(self, processor: InputProcessor):
        """Test redaction of multiple PII types"""
        user_input = "邮箱 test@example.com，电话 123-456-7890"
        redacted, input_hash, pii_flags = processor.redact_user_input(user_input)

        assert "test@example.com" not in redacted
        assert "123-456-7890" not in redacted
        assert "[EMAIL_REDACTED]" in redacted
        assert "[PHONE_REDACTED]" in redacted
        assert set(pii_flags) == {"email", "phone"}

    def test_no_pii_detection(self, processor: InputProcessor):
        """Test input without PII"""
        user_input = "我想要一个关于失眠的视频"
        redacted, input_hash, pii_flags = processor.redact_user_input(user_input)

        assert redacted == user_input
        assert len(pii_flags) == 0
        assert input_hash

    def test_detect_language_chinese(self, processor: InputProcessor):
        """Test Chinese language detection"""
        user_input = "你好，这是一段中文文本"
        lang = processor.detect_language(user_input)
        assert lang == "zh-CN"

    def test_detect_language_english(self, processor: InputProcessor):
        """Test English language detection"""
        user_input = "Hello, this is English text"
        lang = processor.detect_language(user_input)
        assert lang == "en-US"

    def test_detect_language_japanese(self, processor: InputProcessor):
        """Test Japanese language detection"""
        user_input = "こんにちは、これは日本語のテキストです"
        lang = processor.detect_language(user_input)
        assert lang == "ja-JP"

    def test_detect_language_mixed(self, processor: InputProcessor):
        """Test mixed language detection (should detect dominant)"""
        user_input = "中文文本和 English text"
        lang = processor.detect_language(user_input)
        # Chinese characters dominate
        assert lang == "zh-CN"

    def test_process_input_complete(self, processor: InputProcessor):
        """Test complete input processing pipeline"""
        user_input = "我的邮箱 test@example.com，想要焦虑主题的视频"

        result = processor.process_input(
            user_input,
            auto_translate=False
        )

        assert result["redacted_text"] != user_input
        assert "[EMAIL_REDACTED]" in result["redacted_text"]
        assert result["detected_language"] == "zh-CN"
        assert result["input_hash"]
        assert result["pii_flags"] == ["email"]
        assert result["translated_text"] is None

    def test_process_input_with_translation(self, processor: InputProcessor, mock_qwen_llm):
        """Test input processing with translation"""
        # This test requires mocking the LLM
        # For now, we'll skip the actual translation test
        user_input = "Hello, I want a video about insomnia"

        result = processor.process_input(
            user_input,
            auto_translate=True,
            target_language="zh-CN"
        )

        assert result["detected_language"] == "en-US"
        # Translation would be tested with proper mocking

    def test_input_hash_consistency(self, processor: InputProcessor):
        """Test that same input produces same hash"""
        user_input = "测试输入文本"
        _, hash1, _ = processor.redact_user_input(user_input)
        _, hash2, _ = processor.redact_user_input(user_input)

        assert hash1 == hash2

    def test_input_hash_uniqueness(self, processor: InputProcessor):
        """Test that different inputs produce different hashes"""
        _, hash1, _ = processor.redact_user_input("输入1")
        _, hash2, _ = processor.redact_user_input("输入2")

        assert hash1 != hash2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
