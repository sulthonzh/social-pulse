from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError
from src.domain.entities.ai_enrichment import AIEnrichment
from src.domain.value_objects.sentiment_label import SentimentLabel


@pytest.mark.unit
class TestAIEnrichmentDefaults:
    def _make_enrichment(self, **overrides: Any) -> AIEnrichment:
        defaults: dict[str, Any] = {
            "silver_post_id": uuid4(),
        }
        defaults.update(overrides)
        return AIEnrichment(**defaults)

    def test_id_auto_generated(self) -> None:
        enrichment = self._make_enrichment()
        assert enrichment.id is not None
        assert isinstance(enrichment.id, UUID)
        UUID(str(enrichment.id))

    def test_ai_version_defaults_to_one(self) -> None:
        enrichment = self._make_enrichment()
        assert enrichment.ai_version == 1

    def test_hashtags_defaults_to_empty_list(self) -> None:
        enrichment = self._make_enrichment()
        assert enrichment.hashtags == []

    def test_mentions_defaults_to_empty_list(self) -> None:
        enrichment = self._make_enrichment()
        assert enrichment.mentions == []

    def test_language_defaults_to_none(self) -> None:
        enrichment = self._make_enrichment()
        assert enrichment.language is None

    def test_topic_label_defaults_to_none(self) -> None:
        enrichment = self._make_enrichment()
        assert enrichment.topic_label is None

    def test_reach_estimate_defaults_to_none(self) -> None:
        enrichment = self._make_enrichment()
        assert enrichment.reach_estimate is None

    def test_sentiment_defaults_to_none(self) -> None:
        enrichment = self._make_enrichment()
        assert enrichment.sentiment is None

    def test_sentiment_confidence_defaults_to_none(self) -> None:
        enrichment = self._make_enrichment()
        assert enrichment.sentiment_confidence is None

    def test_metadata_model_name_defaults_to_none(self) -> None:
        enrichment = self._make_enrichment()
        assert enrichment.metadata_model_name is None

    def test_metadata_model_version_defaults_to_none(self) -> None:
        enrichment = self._make_enrichment()
        assert enrichment.metadata_model_version is None

    def test_sentiment_model_name_defaults_to_none(self) -> None:
        enrichment = self._make_enrichment()
        assert enrichment.sentiment_model_name is None

    def test_sentiment_model_version_defaults_to_none(self) -> None:
        enrichment = self._make_enrichment()
        assert enrichment.sentiment_model_version is None

    def test_created_at_auto_populated(self) -> None:
        enrichment = self._make_enrichment()
        assert enrichment.created_at is not None
        assert isinstance(enrichment.created_at, datetime)


@pytest.mark.unit
class TestAIEnrichmentExplicitValues:
    def _make_enrichment(self, **overrides: Any) -> AIEnrichment:
        defaults: dict[str, Any] = {
            "silver_post_id": uuid4(),
        }
        defaults.update(overrides)
        return AIEnrichment(**defaults)

    def test_explicit_sentiment_positive(self) -> None:
        enrichment = self._make_enrichment(sentiment=SentimentLabel.POSITIVE)
        assert enrichment.sentiment == SentimentLabel.POSITIVE

    def test_explicit_sentiment_negative(self) -> None:
        enrichment = self._make_enrichment(sentiment=SentimentLabel.NEGATIVE)
        assert enrichment.sentiment == SentimentLabel.NEGATIVE

    def test_explicit_sentiment_neutral(self) -> None:
        enrichment = self._make_enrichment(sentiment=SentimentLabel.NEUTRAL)
        assert enrichment.sentiment == SentimentLabel.NEUTRAL

    def test_explicit_hashtags(self) -> None:
        enrichment = self._make_enrichment(hashtags=["python", "ai", "data"])
        assert enrichment.hashtags == ["python", "ai", "data"]

    def test_explicit_mentions(self) -> None:
        enrichment = self._make_enrichment(mentions=["@user1", "@user2"])
        assert enrichment.mentions == ["@user1", "@user2"]

    def test_explicit_language(self) -> None:
        enrichment = self._make_enrichment(language="en")
        assert enrichment.language == "en"

    def test_explicit_topic_label(self) -> None:
        enrichment = self._make_enrichment(topic_label="technology")
        assert enrichment.topic_label == "technology"

    def test_explicit_reach_estimate(self) -> None:
        enrichment = self._make_enrichment(reach_estimate=50000)
        assert enrichment.reach_estimate == 50000

    def test_explicit_sentiment_confidence(self) -> None:
        enrichment = self._make_enrichment(sentiment_confidence=0.95)
        assert enrichment.sentiment_confidence == 0.95

    def test_explicit_metadata_models(self) -> None:
        enrichment = self._make_enrichment(
            metadata_model_name="gpt-4",
            metadata_model_version="2024-01",
            sentiment_model_name="sentiment-v2",
            sentiment_model_version="2.0",
        )
        assert enrichment.metadata_model_name == "gpt-4"
        assert enrichment.metadata_model_version == "2024-01"
        assert enrichment.sentiment_model_name == "sentiment-v2"
        assert enrichment.sentiment_model_version == "2.0"

    def test_explicit_ai_version(self) -> None:
        enrichment = self._make_enrichment(ai_version=3)
        assert enrichment.ai_version == 3

    def test_explicit_id_override(self) -> None:
        explicit_id = uuid4()
        enrichment = self._make_enrichment(id=explicit_id)
        assert enrichment.id == explicit_id


@pytest.mark.unit
class TestAIEnrichmentRequiredFields:
    def test_silver_post_id_is_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            AIEnrichment()  # type: ignore[call-arg]
