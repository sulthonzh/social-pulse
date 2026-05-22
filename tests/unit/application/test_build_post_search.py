from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from src.application.use_cases.build_post_search import BuildPostSearch
from src.domain.entities.ai_enrichment import AIEnrichment
from src.domain.entities.enriched_post import EnrichedPost
from src.domain.value_objects.platform import Platform
from src.domain.value_objects.sentiment_label import SentimentLabel

if TYPE_CHECKING:
    from src.domain.entities.gold_post_search import GoldPostSearch


def _make_enriched_post(**overrides: object) -> EnrichedPost:
    defaults: dict[str, object] = {
        "id": uuid4(),
        "bronze_post_id": uuid4(),
        "search_request_id": uuid4(),
        "platform": Platform.TWITTER,
        "author_handle": "data_nerd",
        "author_name": "Data Nerd",
        "post_text": "I love data engineering",
        "posted_at": datetime(2025, 1, 15, 10, 0, 0),
        "like_count": 42,
        "share_count": 5,
        "reply_count": 3,
        "view_count": 1000,
        "post_url": "https://x.com/data_nerd/status/123",
    }
    defaults.update(overrides)
    return EnrichedPost.model_validate(defaults)


def _make_ai_enrichment(post_id: UUID, **overrides: object) -> AIEnrichment:
    defaults: dict[str, object] = {
        "silver_post_id": post_id,
        "hashtags": ["data", "engineering"],
        "mentions": ["@friend"],
        "language": "en",
        "topic_label": "technology",
        "topic_confidence": 0.85,
        "sentiment": SentimentLabel.POSITIVE,
        "sentiment_confidence": 0.95,
    }
    defaults.update(overrides)
    return AIEnrichment.model_validate(defaults)


def _build_use_case():
    enriched_post_repo = MagicMock(spec=["get_by_search"])
    ai_enrichment_repo = MagicMock(spec=["get_by_posts"])
    gold_post_search_repo = MagicMock(spec=["save_batch"])
    use_case = BuildPostSearch(
        enriched_post_repo=enriched_post_repo,
        ai_enrichment_repo=ai_enrichment_repo,
        gold_post_search_repo=gold_post_search_repo,
    )
    return use_case, enriched_post_repo, ai_enrichment_repo, gold_post_search_repo


@pytest.mark.unit
class TestBuildPostSearch:
    async def test_execute_materializes_posts_with_ai_enrichment(self):
        use_case, enriched_repo, ai_repo, gold_repo = _build_use_case()
        search_request_id = uuid4()
        post = _make_enriched_post(search_request_id=search_request_id)
        enrichment = _make_ai_enrichment(post.id)
        enriched_repo.get_by_search.return_value = [post]
        ai_repo.get_by_posts.return_value = {str(post.id): enrichment}
        gold_repo.save_batch.return_value = 1

        result = await use_case.execute(str(search_request_id), keyword="python")

        assert result == 1
        enriched_repo.get_by_search.assert_called_once_with(str(search_request_id))
        ai_repo.get_by_posts.assert_called_once_with([str(post.id)])
        saved_posts: list[GoldPostSearch] = gold_repo.save_batch.call_args[0][0]
        assert len(saved_posts) == 1
        saved = saved_posts[0]
        assert saved.search_request_id == search_request_id
        assert saved.keyword == "python"
        assert saved.sentiment == "positive"
        assert saved.sentiment_confidence == 0.95
        assert saved.topic_label == "technology"
        assert saved.language == "en"
        assert saved.hashtags == ["data", "engineering"]

    async def test_execute_handles_missing_ai_enrichment(self):
        use_case, enriched_repo, ai_repo, gold_repo = _build_use_case()
        search_request_id = uuid4()
        post = _make_enriched_post(search_request_id=search_request_id)
        enriched_repo.get_by_search.return_value = [post]
        ai_repo.get_by_posts.return_value = {}
        gold_repo.save_batch.return_value = 1

        result = await use_case.execute(str(search_request_id), keyword="python")

        assert result == 1
        saved_posts: list[GoldPostSearch] = gold_repo.save_batch.call_args[0][0]
        saved = saved_posts[0]
        assert saved.sentiment is None
        assert saved.hashtags == []
        assert saved.mentions == []
        assert saved.ai_version == 1

    async def test_execute_returns_zero_when_no_posts(self):
        use_case, enriched_repo, ai_repo, gold_repo = _build_use_case()
        enriched_repo.get_by_search.return_value = []

        result = await use_case.execute(str(uuid4()), keyword="python")

        assert result == 0
        ai_repo.get_by_posts.assert_not_called()
        gold_repo.save_batch.assert_not_called()
