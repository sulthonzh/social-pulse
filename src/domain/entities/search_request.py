from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.domain.value_objects.crawl_status import CrawlStatus
from src.domain.value_objects.platform import Platform


class SearchRequest(BaseModel):
    """Maps to bronze.search_requests table."""

    model_config = ConfigDict(strict=True)

    id: UUID = Field(default_factory=uuid4)
    keyword: str
    start_date: date
    end_date: date
    platform: Platform = Platform.TWITTER
    status: CrawlStatus = CrawlStatus.PENDING
    posts_found: int = 0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )

    @field_validator("keyword")
    @staticmethod
    def _keyword_must_be_non_empty(v: str) -> str:
        if not v.strip():
            msg = "keyword must be non-empty"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def _date_range_valid(self) -> SearchRequest:
        if self.end_date < self.start_date:
            msg = f"end_date ({self.end_date}) must be >= start_date ({self.start_date})"
            raise ValueError(msg)
        return self
