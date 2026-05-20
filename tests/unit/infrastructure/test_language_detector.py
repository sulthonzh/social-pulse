from __future__ import annotations

import asyncio
from enum import Enum

import pytest
from src.infrastructure.ai.language_detector import LinguaLanguageDetector


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class _FakeIsoCode(Enum):
    EN = "en"
    ID = "id"


class _FakeLanguage(Enum):
    ENGLISH = "english"
    INDONESIAN = "indonesian"

    @property
    def iso_code_639_1(self):
        mapping = {
            _FakeLanguage.ENGLISH: _FakeIsoCode.EN,
            _FakeLanguage.INDONESIAN: _FakeIsoCode.ID,
        }
        return mapping[self]


class _FakeDetector:
    def __init__(self, return_value):
        self._return_value = return_value

    def detect_language(self, text):
        return self._return_value


@pytest.mark.unit
class TestLinguaLanguageDetector:

    def test_empty_string_returns_unknown(self):
        detector = _FakeDetector(None)
        ld = LinguaLanguageDetector(detector=detector)
        result = _run(ld.detect(""))
        assert result.language_code == "unknown"
        assert result.confidence == 0.0

    def test_whitespace_returns_unknown(self):
        detector = _FakeDetector(None)
        ld = LinguaLanguageDetector(detector=detector)
        result = _run(ld.detect("   \t\n"))
        assert result.language_code == "unknown"
        assert result.confidence == 0.0

    def test_no_detection_returns_unknown(self):
        detector = _FakeDetector(None)
        ld = LinguaLanguageDetector(detector=detector)
        result = _run(ld.detect("abc def"))
        assert result.language_code == "unknown"
        assert result.confidence == 0.0

    def test_detects_english(self):
        detector = _FakeDetector(_FakeLanguage.ENGLISH)
        ld = LinguaLanguageDetector(detector=detector)
        result = _run(ld.detect("This is English text"))
        assert result.language_code == "en"
        assert result.confidence == 1.0

    def test_detects_indonesian(self):
        detector = _FakeDetector(_FakeLanguage.INDONESIAN)
        ld = LinguaLanguageDetector(detector=detector)
        result = _run(ld.detect("Ini adalah teks bahasa Indonesia"))
        assert result.language_code == "id"
        assert result.confidence == 1.0
