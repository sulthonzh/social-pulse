from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError
from src.domain.entities.sentiment_result import SentimentResult
from src.domain.value_objects.sentiment_label import SentimentLabel


@pytest.mark.unit
class TestSentimentResultCreation:
    def _make_result(self, **overrides: object) -> SentimentResult:
        defaults: dict[str, object] = {
            "label": SentimentLabel.POSITIVE,
            "confidence": 0.95,
            "model_name": "sentiment-v2",
            "model_version": "2.0",
        }
        defaults.update(overrides)
        return SentimentResult(**defaults)  # type: ignore[arg-type]

    def test_positive_result(self) -> None:
        result = self._make_result(label=SentimentLabel.POSITIVE)
        assert result.label == SentimentLabel.POSITIVE

    def test_negative_result(self) -> None:
        result = self._make_result(label=SentimentLabel.NEGATIVE)
        assert result.label == SentimentLabel.NEGATIVE

    def test_neutral_result(self) -> None:
        result = self._make_result(label=SentimentLabel.NEUTRAL)
        assert result.label == SentimentLabel.NEUTRAL

    def test_confidence_value(self) -> None:
        result = self._make_result(confidence=0.85)
        assert result.confidence == 0.85

    def test_model_name(self) -> None:
        result = self._make_result(model_name="gpt-4")
        assert result.model_name == "gpt-4"

    def test_model_version(self) -> None:
        result = self._make_result(model_version="3.5")
        assert result.model_version == "3.5"


@pytest.mark.unit
class TestSentimentResultConfidenceBounds:
    def _make_result(self, confidence: float) -> SentimentResult:
        return SentimentResult(
            label=SentimentLabel.POSITIVE,
            confidence=confidence,
            model_name="sentiment-v2",
            model_version="2.0",
        )

    def test_confidence_zero_is_valid(self) -> None:
        result = self._make_result(confidence=0.0)
        assert result.confidence == 0.0

    def test_confidence_one_is_valid(self) -> None:
        result = self._make_result(confidence=1.0)
        assert result.confidence == 1.0

    def test_confidence_midpoint_is_valid(self) -> None:
        result = self._make_result(confidence=0.5)
        assert result.confidence == 0.5

    def test_confidence_above_one_raises(self) -> None:
        with pytest.raises(PydanticValidationError):
            self._make_result(confidence=1.1)

    def test_confidence_negative_raises(self) -> None:
        with pytest.raises(PydanticValidationError):
            self._make_result(confidence=-0.1)

    def test_confidence_far_above_one_raises(self) -> None:
        with pytest.raises(PydanticValidationError):
            self._make_result(confidence=5.0)

    def test_confidence_far_below_zero_raises(self) -> None:
        with pytest.raises(PydanticValidationError):
            self._make_result(confidence=-10.0)


@pytest.mark.unit
class TestSentimentResultRequiredFields:
    def test_label_is_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            SentimentResult(  # type: ignore[call-arg]
                confidence=0.9,
                model_name="m",
                model_version="v",
            )

    def test_model_name_is_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            SentimentResult(  # type: ignore[call-arg]
                label=SentimentLabel.POSITIVE,
                confidence=0.9,
                model_version="v",
            )

    def test_model_version_is_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            SentimentResult(  # type: ignore[call-arg]
                label=SentimentLabel.POSITIVE,
                confidence=0.9,
                model_name="m",
            )
