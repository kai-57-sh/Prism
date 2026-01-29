"""
Input Processor - User input redaction, language detection, and translation
"""

import re
import hashlib
from typing import Dict, List, Any, Optional, Tuple

from src.config.settings import settings
from src.config.constants import SUPPORTED_LANGUAGES


class InputProcessor:
    """
    Process user input with PII redaction, language detection, and optional translation
    """

    # PII patterns for redaction
    PII_PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        "ip_address": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
    }

    def __init__(self, llm: Optional[Any] = None):
        """Initialize input processor using ModelScope OpenAI-compatible endpoint."""
        self.llm = llm

    def _ensure_llm(self) -> None:
        if self.llm is None:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=settings.qwen_model,
                api_key=settings.modelscope_api_key,
                base_url=settings.modelscope_base_url,
                temperature=0.0,
            )

    def redact_user_input(self, user_input: str) -> Tuple[str, str, List[str]]:
        """
        Redact PII from user input

        Args:
            user_input: Raw user input text

        Returns:
            Tuple of (redacted_text, input_hash, pii_flags)
        """
        redacted = user_input
        pii_flags = []

        # Apply PII redaction patterns
        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = re.findall(pattern, redacted)
            if matches:
                pii_flags.append(pii_type)
                redacted = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", redacted)

        # Generate hash of original input
        input_hash = hashlib.sha256(user_input.encode()).hexdigest()

        return redacted, input_hash, pii_flags

    def detect_language(self, user_input: str) -> str:
        """
        Detect language of user input

        Args:
            user_input: User input text

        Returns:
            Detected language code (e.g., "zh-CN", "en-US")
        """
        # Simple heuristic-based detection
        # In production, use a proper language detection library

        non_space_chars = [c for c in user_input if not c.isspace()]
        total_chars = len(non_space_chars) or 1

        # Check for Japanese-specific characters first
        japanese_chars = len(
            [
                c for c in non_space_chars
                if '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff'
            ]
        )
        if japanese_chars / total_chars > 0.2:
            return "ja-JP"

        # Check for Chinese characters
        chinese_chars = len([c for c in non_space_chars if '\u4e00' <= c <= '\u9fff'])
        if chinese_chars / total_chars > 0.2:
            return "zh-CN"

        # Default to English
        return "en-US"

    def translate_input(self, user_input: str, target_language: str = "zh-CN") -> str:
        """
        Translate user input to target language

        Args:
            user_input: User input text
            target_language: Target language code

        Returns:
            Translated text
        """
        # Use LLM for translation
        prompt = f"""Translate the following text to {target_language}. Only return the translated text, no explanations.

Text: {user_input}

Translation:"""

        try:
            self._ensure_llm()
            from langchain.schema import HumanMessage
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception as e:
            # If translation fails, return original
            return user_input

    def process_input(
        self,
        user_input: str,
        auto_translate: bool = False,
        target_language: str = "zh-CN",
        align_bilingual: bool = True,
        align_target_language: str = "en-US",
    ) -> Dict[str, Any]:
        """
        Process user input with redaction, language detection, and optional translation

        Args:
            user_input: Raw user input
            auto_translate: Whether to auto-translate to target language
            target_language: Target language for translation
            align_bilingual: Whether to align input with a secondary language
            align_target_language: Language for alignment (default en-US)

        Returns:
            Dict with redacted_text, input_hash, pii_flags, detected_language, translated_text,
            aligned_text, aligned_translation
        """
        # Redact PII
        redacted_text, input_hash, pii_flags = self.redact_user_input(user_input)

        # Detect language
        detected_language = self.detect_language(user_input)

        # Translate if needed
        translated_text = None
        if auto_translate and detected_language != target_language:
            translated_text = self.translate_input(redacted_text, target_language)

        # Align bilingual text if needed (for template matching)
        aligned_text = redacted_text
        aligned_translation = None
        if align_bilingual and detected_language != align_target_language:
            aligned_translation = self.translate_input(redacted_text, align_target_language)
            if aligned_translation and aligned_translation != redacted_text:
                aligned_text = (
                    f"{redacted_text}\n\n"
                    f"[Aligned Translation: {align_target_language}]\n{aligned_translation}"
                )

        return {
            "redacted_text": redacted_text,
            "input_hash": input_hash,
            "pii_flags": pii_flags,
            "detected_language": detected_language,
            "translated_text": translated_text,
            "aligned_text": aligned_text,
            "aligned_translation": aligned_translation,
        }
