from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from src.domain.entities.gold_post_search import GoldPostSearch

if TYPE_CHECKING:
    from src.domain.interfaces import (
        AIEnrichmentRepository,
        EnrichedPostRepository,
        GoldPostSearchRepository,
    )

logger = structlog.get_logger(__name__)


class BuildPostSearch:

    def __init__(
        self,
        enriched_post_repo: EnrichedPostRepository,
        ai_enrichment_repo: AIEnrichmentRepository,
        gold_post_search_repo: GoldPostSearchRepository,
    ) -> None:
        self._enriched_post_repo = enriched_post_repo
        self._ai_enrichment_repo = ai_enrichment_repo
        self._gold_post_search_repo = gold_post_search_repo

    async def execute(self, search_request_id: str, keyword: str) -> int:
        enriched_posts = self._enriched_post_repo.get_by_search(search_request_id)

        if not enriched_posts:
            logger.info(
                "build_post_search.no_posts",
                search_request_id=search_request_id,
            )
            return 0

        gold_posts: list[GoldPostSearch] = []
        for post in enriched_posts:
            enrichment = self._ai_enrichment_repo.get_by_post(str(post.id))
            gold_post = GoldPostSearch(
                search_request_id=post.search_request_id,
                keyword=keyword,
                platform=post.platform,
                author_handle=post.author_handle,
                author_name=post.author_name,
                post_text=post.post_text,
                posted_at=post.posted_at,
                post_url=post.post_url,
                sentiment=enrichment.sentiment.value if enrichment and enrichment.sentiment else None,
                sentiment_confidence=enrichment.sentiment_confidence if enrichment else None,
                topic_label=enrichment.topic_label if enrichment else None,
                language=enrichment.language if enrichment else None,
                hashtags=enrichment.hashtags if enrichment else [],
                mentions=enrichment.mentions if enrichment else [],
                like_count=post.like_count,
                share_count=post.share_count,
                reply_count=post.reply_count,
                view_count=post.view_count,
                ai_version=enrichment.ai_version if enrichment else 1,
            )
            gold_posts.append(gold_post)

        inserted = self._gold_post_search_repo.save_batch(gold_posts)

        logger.info(
            "build_post_search.completed",
            search_request_id=search_request_id,
            total=len(gold_posts),
            inserted=inserted,
        )
        return inserted
