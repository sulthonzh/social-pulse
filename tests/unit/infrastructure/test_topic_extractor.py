from __future__ import annotations

import asyncio

import pytest
from src.infrastructure.ai.topic_extractor import KeyBERTTopicExtractor


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.mark.unit
class TestKeyBERTTopicExtractor:
    def _make_extractor(self, return_value):
        class MockKeyBERT:
            def extract_keywords(self, doc, **kwargs):
                return return_value

        return KeyBERTTopicExtractor(kw_model=MockKeyBERT())

    def test_empty_string_returns_unknown(self):
        extractor = self._make_extractor([])
        result = _run(extractor.extract(""))
        assert result.topic_label == "unknown"

    def test_whitespace_returns_unknown(self):
        extractor = self._make_extractor([])
        result = _run(extractor.extract("   \t\n"))
        assert result.topic_label == "unknown"

    def test_no_keywords_returns_unknown(self):
        extractor = self._make_extractor([])
        result = _run(extractor.extract("some text here"))
        assert result.topic_label == "unknown"

    def test_extracts_single_keyword(self):
        extractor = self._make_extractor([("machine learning", 0.85)])
        result = _run(extractor.extract("I love machine learning"))
        assert result.topic_label == "machine learning"

    def test_result_contains_model_name(self):
        extractor = self._make_extractor([("python", 0.9)])
        result = _run(extractor.extract("python is great"))
        assert result.model_name == "all-MiniLM-L6-v2"
        assert result.model_version == "unknown"
