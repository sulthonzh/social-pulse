from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.domain.value_objects.platform import Platform  # noqa: TC001


class GoldCampaignDaily(BaseModel):
    """Maps to gold.gold_campaign_daily — daily aggregation per campaign."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    search_request_id: UUID
    keyword: str
    platform: Platform
    date: date
    total_posts: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    avg_confidence: float | None = None
    top_hashtags: list[str] = Field(default_factory=list)
    top_topics: list[str] = Field(default_factory=list)
    total_likes: int = 0
    total_shares: int = 0
    total_replies: int = 0
    total_views: int = 0
    ai_version: int = 1
    source_crawl_run_id: str | None = None
    enrichment_job_id: str | None = None
    lineage_updated_at: datetime | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
