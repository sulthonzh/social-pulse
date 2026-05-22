from __future__ import annotations

import pytest
from src.domain.value_objects.ai_job_status import AIJobStatus
from src.domain.value_objects.ai_job_type import AIJobType
from src.domain.value_objects.sentiment_label import SentimentLabel


@pytest.mark.unit
class TestSentimentLabelEnumValues:
    def test_positive_exists(self) -> None:
        assert SentimentLabel.POSITIVE is not None

    def test_negative_exists(self) -> None:
        assert SentimentLabel.NEGATIVE is not None

    def test_neutral_exists(self) -> None:
        assert SentimentLabel.NEUTRAL is not None

    def test_positive_string_value(self) -> None:
        assert SentimentLabel.POSITIVE.value == "positive"

    def test_negative_string_value(self) -> None:
        assert SentimentLabel.NEGATIVE.value == "negative"

    def test_neutral_string_value(self) -> None:
        assert SentimentLabel.NEUTRAL.value == "neutral"


@pytest.mark.unit
class TestSentimentLabelStrEnumBehavior:
    def test_is_string(self) -> None:
        assert isinstance(SentimentLabel.POSITIVE, str)

    def test_value_lookup_positive(self) -> None:
        assert SentimentLabel("positive") is SentimentLabel.POSITIVE

    def test_value_lookup_negative(self) -> None:
        assert SentimentLabel("negative") is SentimentLabel.NEGATIVE

    def test_value_lookup_neutral(self) -> None:
        assert SentimentLabel("neutral") is SentimentLabel.NEUTRAL

    def test_iteration(self) -> None:
        members = list(SentimentLabel)
        assert len(members) == 3
        assert SentimentLabel.POSITIVE in members
        assert SentimentLabel.NEGATIVE in members
        assert SentimentLabel.NEUTRAL in members

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            SentimentLabel("unknown")


@pytest.mark.unit
class TestAIJobStatusEnumValues:
    def test_pending_exists(self) -> None:
        assert AIJobStatus.PENDING is not None

    def test_running_exists(self) -> None:
        assert AIJobStatus.RUNNING is not None

    def test_completed_exists(self) -> None:
        assert AIJobStatus.COMPLETED is not None

    def test_failed_exists(self) -> None:
        assert AIJobStatus.FAILED is not None

    def test_pending_string_value(self) -> None:
        assert AIJobStatus.PENDING.value == "pending"

    def test_running_string_value(self) -> None:
        assert AIJobStatus.RUNNING.value == "running"

    def test_completed_string_value(self) -> None:
        assert AIJobStatus.COMPLETED.value == "completed"

    def test_failed_string_value(self) -> None:
        assert AIJobStatus.FAILED.value == "failed"


@pytest.mark.unit
class TestAIJobStatusStrEnumBehavior:
    def test_is_string(self) -> None:
        assert isinstance(AIJobStatus.RUNNING, str)

    def test_value_lookup_running(self) -> None:
        assert AIJobStatus("running") is AIJobStatus.RUNNING

    def test_value_lookup_completed(self) -> None:
        assert AIJobStatus("completed") is AIJobStatus.COMPLETED

    def test_value_lookup_pending(self) -> None:
        assert AIJobStatus("pending") is AIJobStatus.PENDING

    def test_value_lookup_failed(self) -> None:
        assert AIJobStatus("failed") is AIJobStatus.FAILED

    def test_iteration(self) -> None:
        members = list(AIJobStatus)
        assert len(members) == 4

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            AIJobStatus("unknown")


@pytest.mark.unit
class TestAIJobTypeEnumValues:
    def test_sentiment_exists(self) -> None:
        assert AIJobType.SENTIMENT is not None

    def test_topic_exists(self) -> None:
        assert AIJobType.TOPIC is not None

    def test_language_exists(self) -> None:
        assert AIJobType.LANGUAGE is not None

    def test_full_enrichment_exists(self) -> None:
        assert AIJobType.FULL_ENRICHMENT is not None

    def test_sentiment_string_value(self) -> None:
        assert AIJobType.SENTIMENT.value == "sentiment"

    def test_topic_string_value(self) -> None:
        assert AIJobType.TOPIC.value == "topic"

    def test_language_string_value(self) -> None:
        assert AIJobType.LANGUAGE.value == "language"

    def test_full_enrichment_string_value(self) -> None:
        assert AIJobType.FULL_ENRICHMENT.value == "full_enrichment"


@pytest.mark.unit
class TestAIJobTypeStrEnumBehavior:
    def test_is_string(self) -> None:
        assert isinstance(AIJobType.SENTIMENT, str)

    def test_value_lookup_sentiment(self) -> None:
        assert AIJobType("sentiment") is AIJobType.SENTIMENT

    def test_value_lookup_topic(self) -> None:
        assert AIJobType("topic") is AIJobType.TOPIC

    def test_value_lookup_language(self) -> None:
        assert AIJobType("language") is AIJobType.LANGUAGE

    def test_value_lookup_full_enrichment(self) -> None:
        assert AIJobType("full_enrichment") is AIJobType.FULL_ENRICHMENT

    def test_iteration(self) -> None:
        members = list(AIJobType)
        assert len(members) == 4
        assert AIJobType.SENTIMENT in members
        assert AIJobType.TOPIC in members
        assert AIJobType.LANGUAGE in members
        assert AIJobType.FULL_ENRICHMENT in members

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            AIJobType("unknown")
