from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Protocol

import structlog

from src.domain.entities.language_result import LanguageResult

if TYPE_CHECKING:
    from lingua import Language

logger = structlog.get_logger()


class _DetectorProtocol(Protocol):
    def detect_language(self, text: str) -> Language | None: ...


class LinguaLanguageDetector:
    def __init__(self, detector: _DetectorProtocol | None = None) -> None:
        self._detector: _DetectorProtocol | None = detector

    def _ensure_detector(self) -> _DetectorProtocol:
        if self._detector is None:
            from lingua import Language, LanguageDetectorBuilder  # noqa: PLC0415

            all_languages = list(Language.all())
            self._detector = (
                LanguageDetectorBuilder.from_languages(*all_languages)
                .with_minimum_relative_distance(0.25)
                .build()
            )
        return self._detector

    async def detect(self, text: str) -> LanguageResult:
        if not text or not text.strip():
            logger.debug("empty_text_language")
            return LanguageResult(language_code="unknown", confidence=0.0)

        detector = self._ensure_detector()
        result = await asyncio.to_thread(detector.detect_language, text)

        if result is None:
            logger.debug("language_not_detected")
            return LanguageResult(language_code="unknown", confidence=0.0)

        code = result.iso_code_639_1.name.lower()
        logger.debug("language_detected", language_code=code)

        return LanguageResult(language_code=code, confidence=1.0)
