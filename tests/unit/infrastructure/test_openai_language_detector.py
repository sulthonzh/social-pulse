from __future__ import annotations

import asyncio
from typing import Any

import pytest
from src.infrastructure.ai.openai_language_detector import (
    OpenAILanguageDetector,
    _parse_response,
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class _MockClient:
    def __init__(self, return_value: dict[str, Any] | None) -> None:
        self._return_value = return_value
        self._model = "glm-4.5-flash"

    async def chat_json(self, **kwargs: Any) -> dict[str, Any]:
        return self._return_value if self._return_value is not None else {}


@pytest.mark.unit
class TestParseResponse:
    def test_detects_english(self):
        result = _parse_response({"language_code": "en", "confidence": 0.99}, "glm-4.5-flash")
        assert result.language_code == "en"
        assert result.confidence == 0.99

    def test_detects_indonesian(self):
        result = _parse_response({"language_code": "id", "confidence": 0.95}, "glm-4.5-flash")
        assert result.language_code == "id"

    def test_missing_code_defaults_unknown(self):
        result = _parse_response({"confidence": 0.5}, "glm-4.5-flash")
        assert result.language_code == "unknown"

    def test_empty_code_defaults_unknown(self):
        result = _parse_response({"language_code": "", "confidence": 0.5}, "glm-4.5-flash")
        assert result.language_code == "unknown"

    def test_code_lowercased(self):
        result = _parse_response({"language_code": "FR", "confidence": 0.9}, "glm-4.5-flash")
        assert result.language_code == "fr"

    def test_confidence_clamped(self):
        result = _parse_response({"language_code": "en", "confidence": -0.1}, "glm-4.5-flash")
        assert result.confidence == 0.0

    def test_model_name_includes_openai_prefix(self):
        result = _parse_response({"language_code": "en", "confidence": 0.9}, "glm-4.5-flash")
        assert result.model_name == "openai/glm-4.5-flash"
        assert result.model_version == "glm-4.5-flash"


@pytest.mark.unit
class TestOpenAILanguageDetector:
    def _make_detector(self, return_value: dict[str, Any] | None) -> OpenAILanguageDetector:
        client = _MockClient(return_value)
        return OpenAILanguageDetector(client=client)

    def test_empty_string_returns_unknown(self):
        detector = self._make_detector({"language_code": "en", "confidence": 0.9})
        result = _run(detector.detect(""))
        assert result.language_code == "unknown"
        assert result.confidence == 0.0

    def test_whitespace_returns_unknown(self):
        detector = self._make_detector({"language_code": "en", "confidence": 0.9})
        result = _run(detector.detect("   \t\n"))
        assert result.language_code == "unknown"

    def test_detects_english(self):
        detector = self._make_detector({"language_code": "en", "confidence": 0.98})
        result = _run(detector.detect("This is English text"))
        assert result.language_code == "en"
        assert result.confidence == 0.98

    def test_detects_indonesian(self):
        detector = self._make_detector({"language_code": "id", "confidence": 0.95})
        result = _run(detector.detect("Ini adalah teks bahasa Indonesia"))
        assert result.language_code == "id"

    def test_empty_api_response_returns_unknown(self):
        detector = self._make_detector(None)
        result = _run(detector.detect("some text"))
        assert result.language_code == "unknown"

    def test_result_contains_model_info(self):
        detector = self._make_detector({"language_code": "fr", "confidence": 0.9})
        result = _run(detector.detect("Bonjour le monde"))
        assert "openai/" in result.model_name
        assert result.model_version == "glm-4.5-flash"
