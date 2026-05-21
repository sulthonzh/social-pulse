from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError
from src.domain.entities.topic_result import TopicResult


@pytest.mark.unit
class TestTopicResultCreation:
    def test_basic_creation(self) -> None:
        result = TopicResult(
            topic_label="technology",
            model_name="topic-v1",
            model_version="1.0",
        )
        assert result.topic_label == "technology"
        assert result.model_name == "topic-v1"
        assert result.model_version == "1.0"

    def test_different_topic(self) -> None:
        result = TopicResult(
            topic_label="sports",
            model_name="classifier",
            model_version="2.0",
        )
        assert result.topic_label == "sports"

    def test_explicit_model_fields(self) -> None:
        result = TopicResult(
            topic_label="finance",
            model_name="gpt-4",
            model_version="2024-01",
        )
        assert result.model_name == "gpt-4"
        assert result.model_version == "2024-01"


@pytest.mark.unit
class TestTopicResultRequiredFields:
    def test_topic_label_is_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            TopicResult(  # type: ignore[call-arg]
                model_name="m",
                model_version="v",
            )

    def test_model_name_is_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            TopicResult(  # type: ignore[call-arg]
                topic_label="t",
                model_version="v",
            )

    def test_model_version_is_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            TopicResult(  # type: ignore[call-arg]
                topic_label="t",
                model_name="m",
            )
