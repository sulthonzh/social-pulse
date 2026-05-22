from __future__ import annotations

import asyncio
from typing import Any

import pytest
from src.infrastructure.ai.openai_topic_extractor import (
    OpenAITopicExtractor,
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
    def test_extracts_topic(self):
        result = _parse_response(
            {"topic_label": "machine learning", "confidence": 0.85}, "glm-4.5-flash"
        )
        assert result.topic_label == "machine learning"
        assert result.confidence == 0.85

    def test_missing_topic_defaults_unknown(self):
        result = _parse_response({"confidence": 0.5}, "glm-4.5-flash")
        assert result.topic_label == "unknown"

    def test_empty_topic_defaults_unknown(self):
        result = _parse_response({"topic_label": "", "confidence": 0.5}, "glm-4.5-flash")
        assert result.topic_label == "unknown"

    def test_confidence_clamped(self):
        result = _parse_response({"topic_label": "ai", "confidence": 2.0}, "glm-4.5-flash")
        assert result.confidence == 1.0

    def test_model_name_includes_openai_prefix(self):
        result = _parse_response({"topic_label": "python", "confidence": 0.9}, "glm-4.5-flash")
        assert result.model_name == "openai/glm-4.5-flash"
        assert result.model_version == "glm-4.5-flash"


@pytest.mark.unit
class TestOpenAITopicExtractor:
    def _make_extractor(self, return_value: dict[str, Any] | None) -> OpenAITopicExtractor:
        client = _MockClient(return_value)
        return OpenAITopicExtractor(client=client)

    def test_empty_string_returns_unknown(self):
        extractor = self._make_extractor({"topic_label": "python", "confidence": 0.9})
        result = _run(extractor.extract(""))
        assert result.topic_label == "unknown"

    def test_whitespace_returns_unknown(self):
        extractor = self._make_extractor({"topic_label": "python", "confidence": 0.9})
        result = _run(extractor.extract("   \t\n"))
        assert result.topic_label == "unknown"

    def test_extracts_topic(self):
        extractor = self._make_extractor({"topic_label": "machine learning", "confidence": 0.85})
        result = _run(extractor.extract("I love machine learning"))
        assert result.topic_label == "machine learning"
        assert result.confidence == 0.85

    def test_empty_api_response_returns_unknown(self):
        extractor = self._make_extractor(None)
        result = _run(extractor.extract("some text"))
        assert result.topic_label == "unknown"

    def test_result_contains_model_info(self):
        extractor = self._make_extractor({"topic_label": "data science", "confidence": 0.88})
        result = _run(extractor.extract("data science rocks"))
        assert "openai/" in result.model_name
        assert result.model_version == "glm-4.5-flash"
