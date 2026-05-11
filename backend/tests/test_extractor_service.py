"""
Unit tests for extractor_service.py

Covers: language detection, garbage text detection.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.extractor_service import _is_garbage_text


class TestLanguageDetection:
    """Tests for detect_language (imported from ocr_service, also used by extractor)."""

    def test_import_detect_language(self):
        """Verify detect_language is importable."""
        from services.ocr_service import detect_language
        assert callable(detect_language)

    def test_pure_chinese(self):
        from services.ocr_service import detect_language
        text = "这是一个关于系统架构的详细说明文档，涵盖了从文件上传到数据处理的完整流程。系统采用模块化设计，支持多种文档格式的解析与转换，并提供了强大的OCR引擎用于图像文字识别。"
        result = detect_language(text)
        assert result in ("ch", "mixed")

    def test_pure_english(self):
        from services.ocr_service import detect_language
        text = "This is a comprehensive document describing the system architecture and workflow. It covers everything from file upload to data processing pipelines. The modular design supports multiple document formats."
        result = detect_language(text)
        assert result == "en"

    def test_empty_text_defaults_to_en(self):
        from services.ocr_service import detect_language
        assert detect_language("") == "en"
        assert detect_language(None) == "en"

    def test_short_text_defaults_to_en(self):
        from services.ocr_service import detect_language
        assert detect_language("Hello") == "en"

    def test_mixed_text(self):
        from services.ocr_service import detect_language
        text = "This document 包含了中英文混合内容 for testing purposes 验证语言检测功能"
        result = detect_language(text)
        # Should detect as mixed since CJK ratio is in (0.15, 0.5]
        assert result in ("mixed", "ch")

    def test_mostly_english_with_few_chinese(self):
        from services.ocr_service import detect_language
        text = ("This is a very long English document that contains just a few Chinese characters "
                "like 你好 scattered throughout. The majority of the content is in English. " * 10)
        result = detect_language(text)
        # CJK ratio should be low, detected as English
        assert result == "en"


class TestGarbageTextDetection:
    """Tests for _is_garbage_text — determines if OCR output is noise."""

    def test_empty_text_is_garbage(self):
        assert _is_garbage_text("") is True
        assert _is_garbage_text(None) is True

    def test_short_text_is_garbage(self):
        assert _is_garbage_text("ab") is True
        assert _is_garbage_text("123") is True

    def test_normal_english_is_not_garbage(self):
        assert _is_garbage_text("The quick brown fox jumps over the lazy dog") is False

    def test_normal_chinese_is_not_garbage(self):
        assert _is_garbage_text("这是一段正常的中文文本内容用于测试垃圾检测函数") is False

    def test_symbols_only_is_garbage(self):
        assert _is_garbage_text("!@#$%^&*()_+-=[]{}|;:',.<>?/~`") is True
        assert _is_garbage_text("───────") is True
        assert _is_garbage_text("········") is True

    def test_mostly_symbols_is_garbage(self):
        # 75% symbols, 25% letters — below 0.25 meaningful ratio
        assert _is_garbage_text("!!! a !!!") is True

    def test_english_with_numbers_is_not_garbage(self):
        assert _is_garbage_text("Revenue increased by 25% to $1,500,000 in Q4 2025") is False
        assert _is_garbage_text("ID: 12345 Status: Active Code: ABC-789") is False

    def test_cjk_with_punctuation_is_not_garbage(self):
        assert _is_garbage_text("这是中文文本，包含标点符号。这也是正常的文本内容！用于测试目的。") is False

    def test_short_meaningful_english_is_valid(self):
        # ≥30% Latin ratio and ≥15 meaningful chars → valid
        assert _is_garbage_text("Chapter 1: Introduction to Machine Learning Techniques") is False

    def test_numbers_contribute_to_meaningful_count(self):
        assert _is_garbage_text("12345678901234567890") is False  # 20 digits

    def test_repeated_single_char_is_garbage(self):
        assert _is_garbage_text("aaaaa aaaaa aaaaa") is False  # 15 Latin chars, mostly letters
        assert _is_garbage_text("----- ----- -----") is True   # No meaningful chars

    def test_real_world_ocr_noise(self):
        # Common OCR artifacts
        assert _is_garbage_text("_ _ _ _ _ _ _ _ _") is True
        assert _is_garbage_text(". . . . . . . . . .") is True
        # Short Latin bursts (<15 meaningful chars) are flagged
        assert _is_garbage_text("ii ii ii") is True
        # Longer Latin text passes
        assert _is_garbage_text("this is actual text content here") is False
