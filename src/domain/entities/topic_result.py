from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TopicResult(BaseModel):
    """Value object for topic extraction output."""

    model_config = ConfigDict(strict=True)

    topic_label: str
    model_name: str
    model_version: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
