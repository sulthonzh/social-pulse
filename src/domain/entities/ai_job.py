from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.domain.value_objects.ai_job_status import AIJobStatus
from src.domain.value_objects.ai_job_type import AIJobType  # noqa: TC001


class AIJob(BaseModel):
    """Maps to silver.ai_jobs table."""

    model_config = ConfigDict(strict=True)

    id: UUID = Field(default_factory=uuid4)
    silver_post_id: UUID
    job_type: AIJobType
    status: AIJobStatus = AIJobStatus.PENDING
    ai_version: int = 1
    attempts: int = 0
    max_attempts: int = 3
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
