from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from src.infrastructure.ai.worker import _resolve_provider
from src.shared.config import Settings


class TestResolveProvider:
    def test_override_set_returns_override(self) -> None:
        assert _resolve_provider("openai") == "openai"

    def test_override_local_returns_local(self) -> None:
        assert _resolve_provider("local") == "local"

    def test_empty_string_falls_back_to_global(self) -> None:
        with patch("src.infrastructure.ai.worker.settings") as mock_settings:
            mock_settings.ai_provider = "openai"
            assert _resolve_provider("") == "openai"

    def test_empty_string_falls_back_to_global_local(self) -> None:
        with patch("src.infrastructure.ai.worker.settings") as mock_settings:
            mock_settings.ai_provider = "local"
            assert _resolve_provider("") == "local"


class TestWorkerAdapterSelection:
    @pytest.mark.asyncio
    async def test_per_feature_provider_overrides(self) -> None:
        fake_settings = Settings(
            ai_provider="local",
            sentiment_provider="openai",
            topic_provider="local",
            language_provider="openai",
            db_path=":memory:",
        )

        with (
            patch("src.infrastructure.ai.worker.settings", fake_settings),
            patch("src.infrastructure.ai.worker.DuckDBPostRepository"),
            patch("src.infrastructure.ai.worker.DuckDBEnrichedPostRepository"),
            patch("src.infrastructure.ai.worker.DuckDBAIEnrichmentRepository"),
            patch("src.infrastructure.ai.worker.DuckDBAIJobRepository"),
            patch("src.infrastructure.ai.worker.OpenAISentimentAnalyzer") as mock_sentiment,
            patch("src.infrastructure.ai.worker.KeyBERTTopicExtractor") as mock_topic,
            patch("src.infrastructure.ai.worker.OpenAILanguageDetector") as mock_lang,
            patch("src.infrastructure.ai.worker.OpenAIClient"),
            patch("src.infrastructure.ai.worker.EnrichPostUseCase"),
        ):
            from src.infrastructure.ai.worker import AIEnrichmentWorker  # noqa: PLC0415

            mock_conn = MagicMock()
            AIEnrichmentWorker(mock_conn)

            mock_sentiment.assert_called_once()
            mock_topic.assert_called_once()
            mock_lang.assert_called_once()

    @pytest.mark.asyncio
    async def test_default_provider_uses_local(self) -> None:
        fake_settings = Settings(
            ai_provider="local",
            sentiment_provider="",
            topic_provider="",
            language_provider="",
            db_path=":memory:",
        )

        with (
            patch("src.infrastructure.ai.worker.settings", fake_settings),
            patch("src.infrastructure.ai.worker.DuckDBPostRepository"),
            patch("src.infrastructure.ai.worker.DuckDBEnrichedPostRepository"),
            patch("src.infrastructure.ai.worker.DuckDBAIEnrichmentRepository"),
            patch("src.infrastructure.ai.worker.DuckDBAIJobRepository"),
            patch("src.infrastructure.ai.worker.TransformerSentimentAnalyzer") as mock_sentiment,
            patch("src.infrastructure.ai.worker.KeyBERTTopicExtractor") as mock_topic,
            patch("src.infrastructure.ai.worker.LinguaLanguageDetector") as mock_lang,
            patch("src.infrastructure.ai.worker.EnrichPostUseCase"),
        ):
            from src.infrastructure.ai.worker import AIEnrichmentWorker  # noqa: PLC0415

            mock_conn = MagicMock()
            AIEnrichmentWorker(mock_conn)

            mock_sentiment.assert_called_once()
            mock_topic.assert_called_once()
            mock_lang.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_openai_provider(self) -> None:
        fake_settings = Settings(
            ai_provider="openai",
            sentiment_provider="",
            topic_provider="",
            language_provider="",
            db_path=":memory:",
        )

        with (
            patch("src.infrastructure.ai.worker.settings", fake_settings),
            patch("src.infrastructure.ai.worker.DuckDBPostRepository"),
            patch("src.infrastructure.ai.worker.DuckDBEnrichedPostRepository"),
            patch("src.infrastructure.ai.worker.DuckDBAIEnrichmentRepository"),
            patch("src.infrastructure.ai.worker.DuckDBAIJobRepository"),
            patch("src.infrastructure.ai.worker.OpenAIClient"),
            patch("src.infrastructure.ai.worker.OpenAISentimentAnalyzer") as mock_sentiment,
            patch("src.infrastructure.ai.worker.OpenAITopicExtractor") as mock_topic,
            patch("src.infrastructure.ai.worker.OpenAILanguageDetector") as mock_lang,
            patch("src.infrastructure.ai.worker.EnrichPostUseCase"),
        ):
            from src.infrastructure.ai.worker import AIEnrichmentWorker  # noqa: PLC0415

            mock_conn = MagicMock()
            AIEnrichmentWorker(mock_conn)

            mock_sentiment.assert_called_once()
            mock_topic.assert_called_once()
            mock_lang.assert_called_once()
