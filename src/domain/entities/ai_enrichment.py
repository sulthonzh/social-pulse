from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.domain.value_objects.sentiment_label import SentimentLabel  # noqa: TC001


class AIEnrichment(BaseModel):
    """Maps to silver.silver_ai_enrichment table."""

    model_config = ConfigDict(strict=True)

    id: UUID = Field(default_factory=uuid4)
    silver_post_id: UUID
    ai_version: int = 1
    hashtags: list[str] = Field(default_factory=list)
    mentions: list[str] = Field(default_factory=list)
    language: str | None = None
    topic_label: str | None = None
    reach_estimate: int | None = None
    sentiment: SentimentLabel | None = None
    sentiment_confidence: float | None = None
    metadata_model_name: str | None = None
    metadata_model_version: str | None = None
    sentiment_model_name: str | None = None
    sentiment_model_version: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
