from __future__ import annotations

from enum import StrEnum


class SentimentLabel(StrEnum):
    """Sentiment classification labels for AI enrichment."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
