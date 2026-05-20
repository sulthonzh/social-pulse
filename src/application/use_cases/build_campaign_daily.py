from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

import structlog

from src.domain.entities.gold_campaign_daily import GoldCampaignDaily
from src.domain.value_objects.platform import Platform

if TYPE_CHECKING:
    from datetime import date

    from src.domain.entities.gold_post_search import GoldPostSearch
    from src.domain.interfaces import (
        GoldCampaignDailyRepository,
        GoldPostSearchRepository,
    )

logger = structlog.get_logger(__name__)


def _top_n(items: list[str], n: int = 5) -> list[str]:
    counter = Counter(items)
    return [item for item, _ in counter.most_common(n)]


class BuildCampaignDaily:

    def __init__(
        self,
        gold_post_search_repo: GoldPostSearchRepository,
        gold_daily_repo: GoldCampaignDailyRepository,
    ) -> None:
        self._gold_post_search_repo = gold_post_search_repo
        self._gold_daily_repo = gold_daily_repo

    async def execute(self, search_request_id: str) -> int:
        posts = self._gold_post_search_repo.get_by_search_request(search_request_id)

        if not posts:
            logger.info(
                "build_campaign_daily.no_posts",
                search_request_id=search_request_id,
            )
            return 0

        by_date: dict[tuple[date, str], list[GoldPostSearch]] = {}
        for post in posts:
            if post.posted_at is None:
                continue
            day = post.posted_at.date()
            key = (day, post.platform.value)
            by_date.setdefault(key, []).append(post)

        records: list[GoldCampaignDaily] = []
        for (day, platform_str), day_posts in by_date.items():
            typed_posts = day_posts
            positive = sum(1 for p in typed_posts if getattr(p, "sentiment", None) == "positive")
            negative = sum(1 for p in typed_posts if getattr(p, "sentiment", None) == "negative")
            neutral = sum(1 for p in typed_posts if getattr(p, "sentiment", None) == "neutral")

            confidences = [
                p.sentiment_confidence for p in typed_posts if p.sentiment_confidence is not None
            ]
            avg_conf = sum(confidences) / len(confidences) if confidences else None

            all_hashtags: list[str] = []
            all_topics: list[str] = []
            for p in typed_posts:
                all_hashtags.extend(p.hashtags)
                if p.topic_label:
                    all_topics.append(p.topic_label)

            record = GoldCampaignDaily(
                search_request_id=typed_posts[0].search_request_id,
                keyword=typed_posts[0].keyword,
                platform=Platform(platform_str),
                date=day,
                total_posts=len(typed_posts),
                positive_count=positive,
                negative_count=negative,
                neutral_count=neutral,
                avg_confidence=round(avg_conf, 4) if avg_conf is not None else None,
                top_hashtags=_top_n(all_hashtags),
                top_topics=_top_n(all_topics),
                total_likes=sum(p.like_count for p in typed_posts),
                total_shares=sum(p.share_count for p in typed_posts),
                total_replies=sum(p.reply_count for p in typed_posts),
                total_views=sum(p.view_count for p in typed_posts),
            )
            records.append(record)

        inserted = self._gold_daily_repo.save_batch(records)

        logger.info(
            "build_campaign_daily.completed",
            search_request_id=search_request_id,
            days=len(records),
            inserted=inserted,
        )
        return inserted
