from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from src.domain.entities.sentiment_result import SentimentResult
from src.domain.value_objects.sentiment_label import SentimentLabel

if TYPE_CHECKING:
    from src.infrastructure.ai.openai_client import OpenAIClient

logger = structlog.get_logger()

_SYSTEM_PROMPT = (
    'You are a sentiment classifier. '
    'Classify the sentiment of the user text as one of: "positive", "negative", "neutral". '
    'Respond with a JSON object with exactly two keys: '
    '"label" (one of "positive", "negative", "neutral") '
    'and "confidence" (a float between 0.0 and 1.0).'
)

_UNKNOWN_RESULT = SentimentResult(
    label=SentimentLabel.NEUTRAL,
    confidence=0.0,
    model_name="openai",
    model_version="unknown",
)


def _parse_response(data: dict[str, object], model: str) -> SentimentResult:
    raw_label = str(data.get("label", "neutral")).lower().strip()
    confidence = float(data.get("confidence", 0.0))
    confidence = max(0.0, min(1.0, confidence))

    try:
        label = SentimentLabel(raw_label)
    except ValueError:
        label = SentimentLabel.NEUTRAL

    version = model.rsplit("/", maxsplit=1)[-1] if "/" in model else model
    return SentimentResult(
        label=label,
        confidence=confidence,
        model_name=f"openai/{model}",
        model_version=version,
    )


class OpenAISentimentAnalyzer:
    def __init__(self, client: OpenAIClient) -> None:
        self._client = client

    async def analyze(self, text: str) -> SentimentResult:
        if not text or not text.strip():
            logger.debug("empty_text_sentiment")
            return _UNKNOWN_RESULT

        data = await self._client.chat_json(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=text[:2000],
        )

        if not data:
            logger.warning("openai_sentiment_empty_response")
            return _UNKNOWN_RESULT

        result = _parse_response(data, self._client._model)
        logger.debug(
            "sentiment_analyzed",
            label=result.label,
            confidence=result.confidence,
            text_len=len(text),
        )
        return result
