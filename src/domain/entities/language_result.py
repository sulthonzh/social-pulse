from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LanguageResult(BaseModel):
    """Value object for language detection output."""

    model_config = ConfigDict(strict=True)

    language_code: str
    confidence: float = Field(ge=0.0, le=1.0)
    model_name: str = "lingua"
    model_version: str = "local"
