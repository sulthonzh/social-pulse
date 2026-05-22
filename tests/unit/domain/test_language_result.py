from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError
from src.domain.entities.language_result import LanguageResult


@pytest.mark.unit
class TestLanguageResultCreation:
    def test_basic_creation(self) -> None:
        result = LanguageResult(language_code="en", confidence=0.99)
        assert result.language_code == "en"
        assert result.confidence == 0.99

    def test_different_language(self) -> None:
        result = LanguageResult(language_code="id", confidence=0.85)
        assert result.language_code == "id"

    def test_low_confidence(self) -> None:
        result = LanguageResult(language_code="fr", confidence=0.3)
        assert result.confidence == 0.3


@pytest.mark.unit
class TestLanguageResultConfidenceBounds:
    def _make_result(self, confidence: float) -> LanguageResult:
        return LanguageResult(language_code="en", confidence=confidence)

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
class TestLanguageResultRequiredFields:
    def test_language_code_is_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            LanguageResult(confidence=0.9)  # type: ignore[call-arg]
