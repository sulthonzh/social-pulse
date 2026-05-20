from __future__ import annotations

from enum import StrEnum


class AIJobType(StrEnum):
    """Types of AI enrichment jobs."""

    SENTIMENT = "sentiment"
    TOPIC = "topic"
    LANGUAGE = "language"
    FULL_ENRICHMENT = "full_enrichment"
