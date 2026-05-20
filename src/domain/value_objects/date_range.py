from __future__ import annotations

from datetime import date  # noqa: TC003

from pydantic import BaseModel, model_validator


class DateRange(BaseModel):
    """Immutable date range value object with validation."""

    start_date: date
    end_date: date

    @model_validator(mode="after")
    def _validate_range(self) -> DateRange:
        if self.end_date < self.start_date:
            msg = f"end_date ({self.end_date}) must be >= start_date ({self.start_date})"
            raise ValueError(msg)
        return self

    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days

    def contains(self, target: date) -> bool:
        return self.start_date <= target <= self.end_date
