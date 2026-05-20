from __future__ import annotations

from enum import StrEnum


class CrawlStatus(StrEnum):
    """Lifecycle status for search requests and crawl runs."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
