from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from src.domain.entities.topic_result import TopicResult
from src.shared.prompts import PromptRegistry

if TYPE_CHECKING:
    from src.infrastructure.ai.openai_client import OpenAIClient

logger = structlog.get_logger()

_SYSTEM_PROMPT = PromptRegistry.get_prompt("topic")

_UNKNOWN_RESULT = TopicResult(
    topic_label="unknown",
    model_name="openai",
    model_version="unknown",
    confidence=0.0,
)


def _parse_response(data: dict[str, object], model: str) -> TopicResult:
    topic_label = str(data.get("topic_label", "unknown")).strip() or "unknown"
    raw_confidence = data.get("confidence", 0.0)
    confidence = float(raw_confidence) if isinstance(raw_confidence, int | float) else 0.0
    confidence = max(0.0, min(1.0, confidence))

    version = model.rsplit("/", maxsplit=1)[-1] if "/" in model else model
    return TopicResult(
        topic_label=topic_label,
        model_name=f"openai/{model}",
        model_version=version,
        confidence=confidence,
    )


class OpenAITopicExtractor:
    def __init__(self, client: OpenAIClient) -> None:
        self._client = client

    async def extract(self, text: str) -> TopicResult:
        if not text or not text.strip():
            logger.debug("empty_text_topic")
            return _UNKNOWN_RESULT

        data = await self._client.chat_json(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=text[:2000],
        )

        if not data:
            logger.warning("openai_topic_empty_response")
            return _UNKNOWN_RESULT

        result = _parse_response(data, self._client.model_name)
        logger.debug(
            "topic_extracted",
            topic=result.topic_label,
            confidence=result.confidence,
            text_len=len(text),
        )
        return result
