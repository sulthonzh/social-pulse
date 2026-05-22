from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.domain.value_objects.platform import Platform  # noqa: TC001


class RawPost(BaseModel):
    """Maps to bronze.bronze_posts table."""

    model_config = ConfigDict(strict=True)

    id: UUID = Field(default_factory=uuid4)
    search_request_id: UUID
    crawl_run_id: UUID
    platform: Platform
    platform_id: str | None = None
    author_handle: str | None = None
    raw_payload: dict[str, Any] | None = None
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
