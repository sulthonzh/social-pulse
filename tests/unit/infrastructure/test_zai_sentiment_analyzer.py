from __future__ import annotations

import asyncio
from typing import Any

import pytest
from src.domain.value_objects.sentiment_label import SentimentLabel
from src.infrastructure.ai.zai_sentiment_analyzer import (
    ZAISentimentAnalyzer,
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
    def test_positive_label(self):
        result = _parse_response({"label": "positive", "confidence": 0.95}, "glm-4.5-flash")
        assert result.label == SentimentLabel.POSITIVE
        assert result.confidence == 0.95

    def test_negative_label(self):
        result = _parse_response({"label": "negative", "confidence": 0.8}, "glm-4.5-flash")
        assert result.label == SentimentLabel.NEGATIVE

    def test_neutral_label(self):
        result = _parse_response({"label": "neutral", "confidence": 0.6}, "glm-4.5-flash")
        assert result.label == SentimentLabel.NEUTRAL

    def test_unknown_label_defaults_neutral(self):
        result = _parse_response({"label": "angry", "confidence": 0.7}, "glm-4.5-flash")
        assert result.label == SentimentLabel.NEUTRAL

    def test_confidence_clamped_to_max(self):
        result = _parse_response({"label": "positive", "confidence": 1.5}, "glm-4.5-flash")
        assert result.confidence == 1.0

    def test_confidence_clamped_to_min(self):
        result = _parse_response({"label": "positive", "confidence": -0.3}, "glm-4.5-flash")
        assert result.confidence == 0.0

    def test_model_name_includes_zai_prefix(self):
        result = _parse_response({"label": "positive", "confidence": 0.9}, "glm-4.5-flash")
        assert result.model_name == "zai/glm-4.5-flash"
        assert result.model_version == "glm-4.5-flash"


@pytest.mark.unit
class TestZAISentimentAnalyzer:
    def _make_analyzer(self, return_value: dict[str, Any] | None) -> ZAISentimentAnalyzer:
        client = _MockClient(return_value)
        return ZAISentimentAnalyzer(client=client)

    def test_empty_string_returns_neutral(self):
        analyzer = self._make_analyzer({"label": "positive", "confidence": 0.9})
        result = _run(analyzer.analyze(""))
        assert result.label == SentimentLabel.NEUTRAL
        assert result.confidence == 0.0

    def test_whitespace_returns_neutral(self):
        analyzer = self._make_analyzer({"label": "positive", "confidence": 0.9})
        result = _run(analyzer.analyze("   \t\n"))
        assert result.label == SentimentLabel.NEUTRAL
        assert result.confidence == 0.0

    def test_positive_sentiment(self):
        analyzer = self._make_analyzer({"label": "positive", "confidence": 0.92})
        result = _run(analyzer.analyze("I love this product"))
        assert result.label == SentimentLabel.POSITIVE
        assert result.confidence == 0.92

    def test_negative_sentiment(self):
        analyzer = self._make_analyzer({"label": "negative", "confidence": 0.87})
        result = _run(analyzer.analyze("This is terrible"))
        assert result.label == SentimentLabel.NEGATIVE
        assert result.confidence == 0.87

    def test_empty_api_response_returns_unknown(self):
        analyzer = self._make_analyzer(None)
        result = _run(analyzer.analyze("some text"))
        assert result.label == SentimentLabel.NEUTRAL
        assert result.confidence == 0.0

    def test_result_contains_model_info(self):
        analyzer = self._make_analyzer({"label": "positive", "confidence": 0.9})
        result = _run(analyzer.analyze("great day"))
        assert "zai/" in result.model_name
        assert result.model_version == "glm-4.5-flash"
