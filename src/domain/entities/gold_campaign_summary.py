from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class GoldCampaignSummary(BaseModel):
    """Maps to gold.gold_campaign_summary — per-campaign summary."""

    model_config = ConfigDict(strict=True, frozen=True)

    id: UUID = Field(default_factory=uuid4)
    search_request_id: UUID
    keyword: str
    start_date: date
    end_date: date
    total_posts: int = 0
    positive_pct: float | None = None
    negative_pct: float | None = None
    neutral_pct: float | None = None
    avg_confidence: float | None = None
    total_engagement: int = 0
    total_likes: int = 0
    total_shares: int = 0
    total_replies: int = 0
    total_views: int = 0
    top_hashtags: list[str] = Field(default_factory=list)
    top_topics: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    ai_version: int = 1
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
