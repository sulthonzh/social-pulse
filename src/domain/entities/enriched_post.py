from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.domain.value_objects.platform import Platform  # noqa: TC001


class EnrichedPost(BaseModel):
    """Maps to silver.silver_posts table."""

    model_config = ConfigDict(strict=True)

    id: UUID = Field(default_factory=uuid4)
    bronze_post_id: UUID
    search_request_id: UUID
    platform: Platform
    platform_id: str | None = None
    author_handle: str | None = None
    author_name: str | None = None
    post_text: str | None = None
    posted_at: datetime | None = None
    like_count: int = 0
    share_count: int = 0
    reply_count: int = 0
    view_count: int = 0
    post_url: str | None = None
    is_retweet: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
