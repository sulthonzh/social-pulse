"""Lightweight in-memory metrics collector for pipeline observability."""

from __future__ import annotations

import threading
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


@dataclass
class PipelineCounters:
    """Thread-safe counters for pipeline operations."""

    crawls_started: int = 0
    crawls_completed: int = 0
    crawls_failed: int = 0
    posts_fetched: int = 0
    enrichments_started: int = 0
    enrichments_completed: int = 0
    enrichments_failed: int = 0
    gold_builds_started: int = 0
    gold_builds_completed: int = 0
    gold_builds_failed: int = 0
    api_requests_total: int = 0
    api_requests_errors: int = 0


class MetricsResponse(BaseModel):
    """Response model for /api/metrics endpoint."""

    uptime_seconds: float
    counters: dict[str, int]
    errors_by_type: dict[str, int]


class MetricsCollector:
    """Singleton metrics collector using thread-safe operations."""

    _instance: MetricsCollector | None = None
    _init_lock: threading.Lock = threading.Lock()
    _counters: PipelineCounters
    _error_counts: Counter[str]
    _lock: threading.Lock
    _started_at: datetime

    def __new__(cls) -> MetricsCollector:
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._counters = PipelineCounters()
                    instance._error_counts = Counter[str]()
                    instance._lock = threading.Lock()
                    instance._started_at = datetime.now(UTC)
                    cls._instance = instance
        return cls._instance

    def increment(self, counter: str, value: int = 1) -> None:
        """Increment a named counter by value."""
        with self._lock:
            current = getattr(self._counters, counter, None)
            if current is not None:
                setattr(self._counters, counter, current + value)
            else:
                logger.warning("unknown_counter", counter=counter)

    def record_error(self, error_type: str) -> None:
        """Record an error by type."""
        with self._lock:
            self._error_counts[error_type] += 1

    def get_snapshot(self) -> dict[str, Any]:
        """Return a snapshot of all metrics as a dict."""
        with self._lock:
            uptime = (datetime.now(UTC) - self._started_at).total_seconds()
            return {
                "uptime_seconds": uptime,
                "counters": {
                    "crawls_started": self._counters.crawls_started,
                    "crawls_completed": self._counters.crawls_completed,
                    "crawls_failed": self._counters.crawls_failed,
                    "posts_fetched": self._counters.posts_fetched,
                    "enrichments_started": self._counters.enrichments_started,
                    "enrichments_completed": self._counters.enrichments_completed,
                    "enrichments_failed": self._counters.enrichments_failed,
                    "gold_builds_started": self._counters.gold_builds_started,
                    "gold_builds_completed": self._counters.gold_builds_completed,
                    "gold_builds_failed": self._counters.gold_builds_failed,
                    "api_requests_total": self._counters.api_requests_total,
                    "api_requests_errors": self._counters.api_requests_errors,
                },
                "errors_by_type": dict(self._error_counts),
            }

    def generate_prometheus_text(self) -> str:
        """Generate metrics in Prometheus text exposition format."""
        snapshot = self.get_snapshot()
        lines: list[str] = []
        lines.append("# HELP socialpulse_uptime_seconds Process uptime in seconds")
        lines.append("# TYPE socialpulse_uptime_seconds gauge")
        lines.append(f"socialpulse_uptime_seconds {snapshot['uptime_seconds']:.2f}")

        lines.append("# HELP socialpulse_pipeline_total Pipeline operation counters")
        lines.append("# TYPE socialpulse_pipeline_total counter")
        for name, value in snapshot["counters"].items():
            lines.append(f'socialpulse_pipeline_total{{operation="{name}"}} {value}')

        lines.append("# HELP socialpulse_errors_total Error counts by type")
        lines.append("# TYPE socialpulse_errors_total counter")
        for error_type, count in snapshot["errors_by_type"].items():
            lines.append(f'socialpulse_errors_total{{error_type="{error_type}"}} {count}')

        lines.append("")
        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all counters (useful for testing)."""
        with self._lock:
            self._counters = PipelineCounters()
            self._error_counts = Counter[str]()
            self._started_at = datetime.now(UTC)


metrics = MetricsCollector()
