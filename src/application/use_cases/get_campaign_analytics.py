from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import duckdb

if TYPE_CHECKING:
    pass


@dataclass(frozen=True)
class CampaignAnalytics:
    search_request_id: str
    keyword: str
    platform: str
    total_posts: int = 0
    positive_pct: float = 0.0
    negative_pct: float = 0.0
    neutral_pct: float = 0.0
    avg_confidence: float = 0.0
    total_likes: int = 0
    total_shares: int = 0
    total_replies: int = 0
    total_views: int = 0
    sentiment_distribution: list[dict[str, Any]] = field(default_factory=list)
    daily_volume: list[dict[str, Any]] = field(default_factory=list)
    top_hashtags: list[dict[str, Any]] = field(default_factory=list)
    top_topics: list[dict[str, Any]] = field(default_factory=list)


class GetCampaignAnalytics:
    """Read campaign analytics from gold tables via direct DuckDB queries."""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def execute(self, search_request_id: str) -> CampaignAnalytics | None:
        row = self._conn.execute(
            """
            SELECT search_request_id, keyword, platform,
                   total_posts, positive_pct, negative_pct, neutral_pct,
                   avg_confidence, total_likes, total_shares,
                   total_replies, total_views, top_hashtags, top_topics
            FROM gold.gold_campaign_summary
            WHERE search_request_id = ?
            """,
            [search_request_id],
        ).fetchone()

        if row is None:
            return self._build_from_post_search(search_request_id)

        return CampaignAnalytics(
            search_request_id=str(row[0]),
            keyword=str(row[1]),
            platform=str(row[2]),
            total_posts=int(row[3]),
            positive_pct=float(row[4] or 0),
            negative_pct=float(row[5] or 0),
            neutral_pct=float(row[6] or 0),
            avg_confidence=float(row[7] or 0),
            total_likes=int(row[8] or 0),
            total_shares=int(row[9] or 0),
            total_replies=int(row[10] or 0),
            total_views=int(row[11] or 0),
            top_hashtags=self._unnest_top(row[12]),
            top_topics=self._unnest_top(row[13]),
            sentiment_distribution=self._get_sentiment_distribution(search_request_id),
            daily_volume=self._get_daily_volume(search_request_id),
        )

    def _build_from_post_search(self, search_request_id: str) -> CampaignAnalytics | None:
        meta = self._conn.execute(
            """
            SELECT search_request_id, keyword, platform
            FROM gold.gold_post_search
            WHERE search_request_id = ?
            LIMIT 1
            """,
            [search_request_id],
        ).fetchone()

        if meta is None:
            return None

        stats = self._conn.execute(
            """
            SELECT
                COUNT(*) as total,
                COALESCE(SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END), 0) as pos,
                COALESCE(SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END), 0) as neg,
                COALESCE(SUM(CASE WHEN sentiment = 'neutral' THEN 1 ELSE 0 END), 0) as neu,
                COALESCE(AVG(sentiment_confidence), 0) as avg_conf,
                COALESCE(SUM(like_count), 0) as likes,
                COALESCE(SUM(share_count), 0) as shares,
                COALESCE(SUM(reply_count), 0) as replies,
                COALESCE(SUM(view_count), 0) as views
            FROM gold.gold_post_search
            WHERE search_request_id = ?
            """,
            [search_request_id],
        ).fetchone()

        total = int(stats[0]) if stats and stats[0] else 0
        pos = int(stats[1]) if stats and stats[1] else 0
        neg = int(stats[2]) if stats and stats[2] else 0
        neu = int(stats[3]) if stats and stats[3] else 0

        return CampaignAnalytics(
            search_request_id=str(meta[0]),
            keyword=str(meta[1]),
            platform=str(meta[2]),
            total_posts=total,
            positive_pct=round(pos / total * 100, 1) if total else 0.0,
            negative_pct=round(neg / total * 100, 1) if total else 0.0,
            neutral_pct=round(neu / total * 100, 1) if total else 0.0,
            avg_confidence=round(float(stats[4]), 3) if stats and stats[4] else 0.0,
            total_likes=int(stats[5]) if stats and stats[5] else 0,
            total_shares=int(stats[6]) if stats and stats[6] else 0,
            total_replies=int(stats[7]) if stats and stats[7] else 0,
            total_views=int(stats[8]) if stats and stats[8] else 0,
            top_hashtags=self._get_top_hashtags_from_posts(search_request_id),
            top_topics=self._get_top_topics_from_posts(search_request_id),
            sentiment_distribution=self._get_sentiment_distribution(search_request_id),
            daily_volume=self._get_daily_volume(search_request_id),
        )

    def _get_sentiment_distribution(self, search_request_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT sentiment, COUNT(*) as cnt
            FROM gold.gold_post_search
            WHERE search_request_id = ? AND sentiment IS NOT NULL
            GROUP BY sentiment
            ORDER BY cnt DESC
            """,
            [search_request_id],
        ).fetchall()
        return [{"sentiment": str(r[0]), "count": int(r[1])} for r in rows]

    def _get_daily_volume(self, search_request_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT CAST(posted_at AS DATE) as day, COUNT(*) as cnt
            FROM gold.gold_post_search
            WHERE search_request_id = ? AND posted_at IS NOT NULL
            GROUP BY day
            ORDER BY day
            """,
            [search_request_id],
        ).fetchall()
        return [{"date": str(r[0]), "count": int(r[1])} for r in rows]

    def _get_top_hashtags_from_posts(self, search_request_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT UNNEST(hashtags) as tag, COUNT(*) as cnt
            FROM gold.gold_post_search
            WHERE search_request_id = ? AND hashtags IS NOT NULL
            GROUP BY tag
            ORDER BY cnt DESC
            LIMIT 10
            """,
            [search_request_id],
        ).fetchall()
        return [{"hashtag": str(r[0]), "count": int(r[1])} for r in rows]

    def _get_top_topics_from_posts(self, search_request_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT topic_label, COUNT(*) as cnt
            FROM gold.gold_post_search
            WHERE search_request_id = ? AND topic_label IS NOT NULL
            GROUP BY topic_label
            ORDER BY cnt DESC
            LIMIT 10
            """,
            [search_request_id],
        ).fetchall()
        return [{"topic": str(r[0]), "count": int(r[1])} for r in rows]

    @staticmethod
    def _unnest_top(arr: Any) -> list[dict[str, Any]]:
        if arr is None:
            return []
        return [{"value": str(v), "count": 0} for v in arr]
