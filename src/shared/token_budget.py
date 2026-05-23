from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


class TokenBudget:
    def __init__(
        self,
        daily_budget: int = 1_000_000,
        hourly_budget: int = 100_000,
    ) -> None:
        self._daily_budget = daily_budget
        self._hourly_budget = hourly_budget
        self._hourly_buckets: dict[str, int] = defaultdict(int)

    def check_budget(self, estimated_tokens: int) -> bool:
        now = datetime.now(UTC)
        hour_key = now.strftime("%Y-%m-%dT%H")
        day_key = now.strftime("%Y-%m-%d")

        hourly_used = self._hourly_buckets[hour_key]
        daily_used = sum(v for k, v in self._hourly_buckets.items() if k.startswith(day_key))

        return not (
            hourly_used + estimated_tokens > self._hourly_budget
            or daily_used + estimated_tokens > self._daily_budget
        )

    def record_usage(self, tokens: int) -> None:
        now = datetime.now(UTC)
        hour_key = now.strftime("%Y-%m-%dT%H")
        self._hourly_buckets[hour_key] += tokens

    def get_usage_summary(self) -> dict[str, int]:
        now = datetime.now(UTC)
        hour_key = now.strftime("%Y-%m-%dT%H")
        day_key = now.strftime("%Y-%m-%d")

        hourly_used = self._hourly_buckets[hour_key]
        daily_used = sum(v for k, v in self._hourly_buckets.items() if k.startswith(day_key))

        return {
            "daily_used": daily_used,
            "daily_budget": self._daily_budget,
            "hourly_used": hourly_used,
            "hourly_budget": self._hourly_budget,
        }

    def _evict_old_buckets(self) -> None:
        cutoff = datetime.now(UTC) - timedelta(hours=25)
        cutoff_key = cutoff.strftime("%Y-%m-%dT%H")
        keys_to_remove = [k for k in self._hourly_buckets if k < cutoff_key]
        for k in keys_to_remove:
            del self._hourly_buckets[k]
