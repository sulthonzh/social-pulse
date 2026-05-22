from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from src.domain.entities.gold_post_search import GoldPostSearch

if TYPE_CHECKING:
    from datetime import datetime

    from src.domain.interfaces import (
        AIEnrichmentRepository,
        EnrichedPostRepository,
        GoldPostSearchRepository,
    )

logger = structlog.get_logger(__name__)

BATCH_SIZE = 1000


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

    async def execute(
        self,
        search_request_id: str,
        keyword: str,
        since: datetime | None = None,
    ) -> int:
        total_inserted = 0
        offset = 0

        while True:
            if since is not None:
                batch = self._enriched_post_repo.get_enriched_since_paginated(
                    search_request_id,
                    since,
                    limit=BATCH_SIZE,
                    offset=offset,
                )
            else:
                batch = self._enriched_post_repo.get_by_search_paginated(
                    search_request_id,
                    limit=BATCH_SIZE,
                    offset=offset,
                )

            if not batch:
                break

            post_ids = [str(post.id) for post in batch]
            enrichment_map = self._ai_enrichment_repo.get_by_posts(post_ids)

            gold_posts: list[GoldPostSearch] = []
            for post in batch:
                enrichment = enrichment_map.get(str(post.id))
                gold_post = GoldPostSearch(
                    search_request_id=post.search_request_id,
                    keyword=keyword,
                    platform=post.platform,
                    author_handle=post.author_handle,
                    author_name=post.author_name,
                    post_text=post.post_text,
                    posted_at=post.posted_at,
                    post_url=post.post_url,
                    sentiment=enrichment.sentiment.value
                    if enrichment and enrichment.sentiment
                    else None,
                    sentiment_confidence=enrichment.sentiment_confidence if enrichment else None,
                    topic_label=enrichment.topic_label if enrichment else None,
                    topic_confidence=enrichment.topic_confidence if enrichment else None,
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
            total_inserted += inserted
            offset += BATCH_SIZE

            if len(batch) < BATCH_SIZE:
                break

        logger.info(
            "build_post_search.completed",
            search_request_id=search_request_id,
            total=total_inserted,
        )
        return total_inserted
