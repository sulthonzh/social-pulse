from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import duckdb

from src.application.use_cases.get_campaign_analytics import CampaignAnalytics


@dataclass(frozen=True)
class CrossCampaignComparison:
    campaigns: list[CampaignAnalytics] = field(default_factory=list)
    sentiment_comparison: list[dict[str, Any]] = field(default_factory=list)
    volume_comparison: list[dict[str, Any]] = field(default_factory=list)
    engagement_comparison: list[dict[str, Any]] = field(default_factory=list)


class GetCrossCampaign:
    """Compare multiple campaigns side by side."""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def execute(self, search_request_ids: list[str]) -> CrossCampaignComparison:
        from src.application.use_cases.get_campaign_analytics import (
            GetCampaignAnalytics,
        )

        analytics_uc = GetCampaignAnalytics(self._conn)
        campaigns: list[CampaignAnalytics] = []

        for rid in search_request_ids:
            result = analytics_uc.execute(rid)
            if result is not None:
                campaigns.append(result)

        if not campaigns:
            return CrossCampaignComparison()

        return CrossCampaignComparison(
            campaigns=campaigns,
            sentiment_comparison=self._build_sentiment_comparison(campaigns),
            volume_comparison=self._build_volume_comparison(campaigns),
            engagement_comparison=self._build_engagement_comparison(campaigns),
        )

    @staticmethod
    def _build_sentiment_comparison(
        campaigns: list[CampaignAnalytics],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for c in campaigns:
            rows.append(
                {
                    "campaign": c.keyword,
                    "positive": c.positive_pct,
                    "negative": c.negative_pct,
                    "neutral": c.neutral_pct,
                }
            )
        return rows

    @staticmethod
    def _build_volume_comparison(
        campaigns: list[CampaignAnalytics],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for c in campaigns:
            for day in c.daily_volume:
                rows.append(
                    {
                        "campaign": c.keyword,
                        "date": day["date"],
                        "count": day["count"],
                    }
                )
        return rows

    @staticmethod
    def _build_engagement_comparison(
        campaigns: list[CampaignAnalytics],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for c in campaigns:
            rows.append(
                {
                    "campaign": c.keyword,
                    "likes": c.total_likes,
                    "shares": c.total_shares,
                    "replies": c.total_replies,
                    "views": c.total_views,
                }
            )
        return rows
