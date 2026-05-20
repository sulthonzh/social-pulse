from __future__ import annotations

from enum import StrEnum


class AIJobStatus(StrEnum):
    """Lifecycle status for AI processing jobs."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
