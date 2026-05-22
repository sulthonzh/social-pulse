from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from src.domain.entities.language_result import LanguageResult

if TYPE_CHECKING:
    from src.infrastructure.ai.openai_client import OpenAIClient

logger = structlog.get_logger()

_SYSTEM_PROMPT = (
    "You are a language detector. "
    "Given the user text, detect the language and respond with a JSON object "
    "with exactly two keys: "
    '"language_code" (ISO 639-1 two-letter code, e.g. "en", "id", "fr") '
    'and "confidence" (float between 0.0 and 1.0).'
)

_UNKNOWN_RESULT = LanguageResult(
    language_code="unknown",
    confidence=0.0,
    model_name="openai",
    model_version="unknown",
)


def _parse_response(data: dict[str, object], model: str) -> LanguageResult:
    language_code = str(data.get("language_code", "unknown")).strip().lower() or "unknown"
    raw_confidence = data.get("confidence", 0.0)
    confidence = float(raw_confidence) if isinstance(raw_confidence, (int, float)) else 0.0
    confidence = max(0.0, min(1.0, confidence))

    version = model.rsplit("/", maxsplit=1)[-1] if "/" in model else model
    return LanguageResult(
        language_code=language_code,
        confidence=confidence,
        model_name=f"openai/{model}",
        model_version=version,
    )


class OpenAILanguageDetector:
    def __init__(self, client: OpenAIClient) -> None:
        self._client = client

    async def detect(self, text: str) -> LanguageResult:
        if not text or not text.strip():
            logger.debug("empty_text_language")
            return _UNKNOWN_RESULT

        data = await self._client.chat_json(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=text[:2000],
        )

        if not data:
            logger.warning("openai_language_empty_response")
            return _UNKNOWN_RESULT

        result = _parse_response(data, self._client._model)
        logger.debug(
            "language_detected",
            language_code=result.language_code,
            confidence=result.confidence,
            text_len=len(text),
        )
        return result
