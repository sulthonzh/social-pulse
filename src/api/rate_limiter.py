"""In-memory sliding-window rate limiter."""

from __future__ import annotations

import threading
import time
from collections import defaultdict


class RateLimiter:
    """Thread-safe sliding-window rate limiter keyed by client identifier."""

    def __init__(self, max_requests: int, window_seconds: int = 60) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._timestamps: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, client_id: str) -> bool:
        """Check whether *client_id* is within the rate limit.

        Prunes stale entries on every call so memory does not grow unbounded.
        """
        now = time.monotonic()
        cutoff = now - self._window_seconds

        with self._lock:
            timestamps = self._timestamps[client_id]
            self._timestamps[client_id] = [ts for ts in timestamps if ts > cutoff]
            timestamps = self._timestamps[client_id]

            if len(timestamps) >= self._max_requests:
                return False

            timestamps.append(now)
            return True

    def reset(self) -> None:
        """Clear all tracked state."""
        with self._lock:
            self._timestamps.clear()
