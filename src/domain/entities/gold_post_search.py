from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.domain.value_objects.platform import Platform  # noqa: TC001


class GoldPostSearch(BaseModel):
    """Maps to gold.gold_post_search — flat denormalized post for search/filter."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    search_request_id: UUID
    keyword: str
    platform: Platform
    author_handle: str | None = None
    author_name: str | None = None
    post_text: str | None = None
    posted_at: datetime | None = None
    post_url: str | None = None
    sentiment: str | None = None
    sentiment_confidence: float | None = None
    topic_label: str | None = None
    topic_confidence: float | None = None
    language: str | None = None
    hashtags: list[str] = Field(default_factory=list)
    mentions: list[str] = Field(default_factory=list)
    like_count: int = 0
    share_count: int = 0
    reply_count: int = 0
    view_count: int = 0
    ai_version: int = 1
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
