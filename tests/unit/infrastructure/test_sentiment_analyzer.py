from __future__ import annotations

import asyncio

import pytest
from src.domain.value_objects.sentiment_label import SentimentLabel
from src.infrastructure.ai.sentiment_analyzer import (
    TransformerSentimentAnalyzer,
    _map_label,
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.mark.unit
class TestMapLabel:
    def test_positive_label(self):
        assert _map_label("positive") == SentimentLabel.POSITIVE

    def test_negative_label(self):
        assert _map_label("negative") == SentimentLabel.NEGATIVE

    def test_neutral_label(self):
        assert _map_label("neutral") == SentimentLabel.NEUTRAL

    def test_label_0_maps_positive(self):
        assert _map_label("Label_0") == SentimentLabel.POSITIVE

    def test_label_2_maps_negative(self):
        assert _map_label("Label_2") == SentimentLabel.NEGATIVE

    def test_label_1_maps_neutral(self):
        assert _map_label("Label_1") == SentimentLabel.NEUTRAL

    def test_unknown_maps_neutral(self):
        assert _map_label("something_else") == SentimentLabel.NEUTRAL


@pytest.mark.unit
class TestTransformerSentimentAnalyzer:
    def _make_analyzer(self, pipeline_return):
        def mock_pipeline(text, **kwargs):
            return pipeline_return

        return TransformerSentimentAnalyzer(pipeline=mock_pipeline)

    def test_empty_string_returns_neutral(self):
        analyzer = self._make_analyzer([])
        result = _run(analyzer.analyze(""))
        assert result.label == SentimentLabel.NEUTRAL
        assert result.confidence == 0.0

    def test_whitespace_returns_neutral(self):
        analyzer = self._make_analyzer([])
        result = _run(analyzer.analyze("   \t\n"))
        assert result.label == SentimentLabel.NEUTRAL
        assert result.confidence == 0.0

    def test_selects_highest_scoring_label(self):
        pipeline_output = [
            [
                {"label": "positive", "score": 0.2},
                {"label": "negative", "score": 0.7},
                {"label": "neutral", "score": 0.1},
            ]
        ]
        analyzer = self._make_analyzer(pipeline_output)
        result = _run(analyzer.analyze("I hate this"))
        assert result.label == SentimentLabel.NEGATIVE
        assert result.confidence == 0.7

    def test_truncates_long_text(self):
        received_texts = []

        def mock_pipeline(text, **kwargs):
            received_texts.append(text)
            return [
                [
                    {"label": "positive", "score": 0.9},
                    {"label": "negative", "score": 0.05},
                    {"label": "neutral", "score": 0.05},
                ]
            ]

        analyzer = TransformerSentimentAnalyzer(pipeline=mock_pipeline)
        long_text = "x" * 1000
        _run(analyzer.analyze(long_text))
        assert len(received_texts[0]) == 512

    def test_result_contains_model_name(self):
        analyzer = self._make_analyzer(
            [
                [
                    {"label": "positive", "score": 0.9},
                    {"label": "negative", "score": 0.05},
                    {"label": "neutral", "score": 0.05},
                ]
            ]
        )
        result = _run(analyzer.analyze("great day"))
        assert result.model_name == "tabularisai/multilingual-sentiment-analysis"
        assert result.model_version == "unknown"
