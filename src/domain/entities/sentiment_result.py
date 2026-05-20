from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.domain.value_objects.sentiment_label import SentimentLabel  # noqa: TC001


class SentimentResult(BaseModel):
    """Value object for sentiment analysis output."""

    model_config = ConfigDict(strict=True)

    label: SentimentLabel
    confidence: float = Field(ge=0.0, le=1.0)
    model_name: str
    model_version: str
