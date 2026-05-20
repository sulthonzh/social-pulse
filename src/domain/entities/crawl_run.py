from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.domain.value_objects.crawl_status import CrawlStatus
from src.domain.value_objects.platform import Platform  # noqa: TC001


class CrawlRun(BaseModel):
    """Maps to bronze.bronze_crawl_runs table."""

    model_config = ConfigDict(strict=True)

    id: UUID = Field(default_factory=uuid4)
    search_request_id: UUID
    platform: Platform
    status: CrawlStatus = CrawlStatus.RUNNING
    posts_fetched: int = 0
    error_message: str | None = None
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
    completed_at: datetime | None = None
