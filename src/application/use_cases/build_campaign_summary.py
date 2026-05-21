from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

import structlog

from src.domain.entities.gold_campaign_summary import GoldCampaignSummary

if TYPE_CHECKING:
    from datetime import date

    from src.domain.interfaces import (
        GoldCampaignSummaryRepository,
        GoldPostSearchRepository,
    )

logger = structlog.get_logger(__name__)


def _top_n(items: list[str], n: int = 5) -> list[str]:
    counter = Counter(items)
    return [item for item, _ in counter.most_common(n)]


class BuildCampaignSummary:
    def __init__(
        self,
        gold_post_search_repo: GoldPostSearchRepository,
        gold_summary_repo: GoldCampaignSummaryRepository,
    ) -> None:
        self._gold_post_search_repo = gold_post_search_repo
        self._gold_summary_repo = gold_summary_repo

    async def execute(
        self,
        search_request_id: str,
        start_date: date,
        end_date: date,
    ) -> GoldCampaignSummary:
        posts = self._gold_post_search_repo.get_by_search_request(search_request_id)

        total = len(posts)
        if total == 0:
            summary = GoldCampaignSummary(
                search_request_id=posts[0].search_request_id
                if posts
                else __import__("uuid").UUID("00000000-0000-0000-0000-000000000000"),
                keyword="",
                start_date=start_date,
                end_date=end_date,
            )
            return self._gold_summary_repo.save(summary)

        positive = sum(1 for p in posts if p.sentiment == "positive")
        negative = sum(1 for p in posts if p.sentiment == "negative")
        neutral = sum(1 for p in posts if p.sentiment == "neutral")

        positive_pct = round(positive / total * 100, 2)
        negative_pct = round(negative / total * 100, 2)
        neutral_pct = round(neutral / total * 100, 2)

        confidences = [p.sentiment_confidence for p in posts if p.sentiment_confidence is not None]
        avg_confidence = round(sum(confidences) / len(confidences), 4) if confidences else None

        all_hashtags: list[str] = []
        all_topics: list[str] = []
        platform_set: set[str] = set()
        for p in posts:
            all_hashtags.extend(p.hashtags)
            if p.topic_label:
                all_topics.append(p.topic_label)
            platform_set.add(p.platform.value)

        total_engagement = sum(p.like_count + p.share_count + p.reply_count for p in posts)

        summary = GoldCampaignSummary(
            search_request_id=posts[0].search_request_id,
            keyword=posts[0].keyword,
            start_date=start_date,
            end_date=end_date,
            total_posts=total,
            positive_pct=positive_pct,
            negative_pct=negative_pct,
            neutral_pct=neutral_pct,
            avg_confidence=avg_confidence,
            total_engagement=total_engagement,
            total_likes=sum(p.like_count for p in posts),
            total_shares=sum(p.share_count for p in posts),
            total_replies=sum(p.reply_count for p in posts),
            total_views=sum(p.view_count for p in posts),
            top_hashtags=_top_n(all_hashtags),
            top_topics=_top_n(all_topics),
            platforms=sorted(platform_set),
        )

        saved = self._gold_summary_repo.save(summary)

        logger.info(
            "build_campaign_summary.completed",
            search_request_id=search_request_id,
            total_posts=total,
        )
        return saved
