from __future__ import annotations

import asyncio
from typing import Any, Protocol, cast

import structlog

from src.domain.entities.sentiment_result import SentimentResult
from src.domain.value_objects.sentiment_label import SentimentLabel

logger = structlog.get_logger()


class _PipelineCallable(Protocol):
    def __call__(self, text: str, **kwargs: Any) -> list[list[dict[str, Any]]]: ...


def _map_label(raw_label: str) -> SentimentLabel:
    normalized = raw_label.lower().strip()
    if normalized in ("positive", "label_0"):
        return SentimentLabel.POSITIVE
    if normalized in ("negative", "label_2"):
        return SentimentLabel.NEGATIVE
    return SentimentLabel.NEUTRAL


class TransformerSentimentAnalyzer:
    def __init__(
        self,
        model_name: str = "tabularisai/multilingual-sentiment-analysis",
        pipeline: _PipelineCallable | None = None,
    ) -> None:
        self._model_name = model_name
        self._pipeline: _PipelineCallable | None = pipeline
        self._loaded = pipeline is not None

    def _ensure_pipeline(self) -> _PipelineCallable:
        if self._pipeline is None:
            from transformers import pipeline as hf_pipeline  # noqa: PLC0415

            self._pipeline = cast(
                "_PipelineCallable",
                hf_pipeline(
                    "text-classification",
                    model=self._model_name,
                    top_k=3,
                ),
            )
            self._loaded = True
        return self._pipeline

    def _get_model_version(self) -> str:
        """Extract model version identifier from model name."""
        if "/" in self._model_name:
            return self._model_name.split("/")[-1]
        return self._model_name

    async def analyze(self, text: str) -> SentimentResult:
        if not text or not text.strip():
            logger.debug("empty_text_sentiment")
            return SentimentResult(
                label=SentimentLabel.NEUTRAL,
                confidence=0.0,
                model_name=self._model_name,
                model_version=self._get_model_version(),
            )

        truncated = text[:512]
        pipe = self._ensure_pipeline()
        raw_nested: list[list[dict[str, Any]]] = await asyncio.to_thread(lambda: pipe(truncated))
        best = max(raw_nested[0], key=lambda r: r["score"])
        label = _map_label(best["label"])
        score = float(best["score"])

        logger.debug(
            "sentiment_analyzed",
            label=label,
            confidence=score,
            text_len=len(truncated),
        )

        return SentimentResult(
            label=label,
            confidence=score,
            model_name=self._model_name,
            model_version=self._get_model_version(),
        )
