from __future__ import annotations

import asyncio
from typing import Protocol

import structlog

from src.domain.entities.topic_result import TopicResult

logger = structlog.get_logger()


class _KeyBERTModel(Protocol):
    def extract_keywords(
        self,
        doc: str,
        keyphrase_ngram_range: tuple[int, int],
        stop_words: str,
        top_n: int,
    ) -> list[tuple[str, float]]: ...


class KeyBERTTopicExtractor:
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        kw_model: _KeyBERTModel | None = None,
    ) -> None:
        self._model_name = model_name
        self._kw_model: _KeyBERTModel | None = kw_model

    def _ensure_model(self) -> _KeyBERTModel:
        if self._kw_model is None:
            from keybert import KeyBERT  # noqa: PLC0415

            self._kw_model = KeyBERT(self._model_name)
        return self._kw_model

    async def extract(self, text: str) -> TopicResult:
        if not text or not text.strip():
            logger.debug("empty_text_topic")
            return TopicResult(
                topic_label="unknown",
                model_name=self._model_name,
                model_version="unknown",
            )

        model = self._ensure_model()
        keywords = await asyncio.to_thread(
            model.extract_keywords,
            text,
            keyphrase_ngram_range=(1, 2),
            stop_words="english",
            top_n=1,
        )

        topic = keywords[0][0] if keywords else "unknown"

        logger.debug("topic_extracted", topic=topic, text_len=len(text))

        return TopicResult(
            topic_label=topic,
            model_name=self._model_name,
            model_version="unknown",
        )
