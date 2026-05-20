from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TopicResult(BaseModel):
    """Value object for topic extraction output."""

    model_config = ConfigDict(strict=True)

    topic_label: str
    model_name: str
    model_version: str
