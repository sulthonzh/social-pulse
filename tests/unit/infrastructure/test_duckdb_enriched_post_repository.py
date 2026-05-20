from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from src.domain.entities.enriched_post import EnrichedPost
from src.domain.value_objects.platform import Platform
from src.infrastructure.persistence.duckdb_enriched_post_repository import (
    DuckDBEnrichedPostRepository,
)


def _make_enriched_post(**overrides) -> EnrichedPost:
    defaults = {
        "id": uuid4(),
        "bronze_post_id": uuid4(),
        "search_request_id": uuid4(),
        "platform": Platform.TWITTER,
        "platform_id": f"tweet_{uuid4().hex[:8]}",
        "author_handle": "testuser",
        "author_name": "Test User",
        "post_text": "Hello world",
        "posted_at": datetime(2025, 1, 15, 10, 0, 0),
        "like_count": 10,
        "share_count": 5,
        "reply_count": 3,
        "view_count": 100,
        "post_url": "https://twitter.com/test/status/123",
        "is_retweet": False,
        "created_at": datetime(2025, 1, 15, 12, 0, 0),
    }
    defaults.update(overrides)
    return EnrichedPost(**defaults)


@pytest.mark.unit
class TestDuckDBEnrichedPostRepository:

    def test_save_returns_entity_with_id(self, db_with_schema):
        repo = DuckDBEnrichedPostRepository(db_with_schema)
        post = _make_enriched_post()
        result = repo.save(post)
        assert result.id == post.id

    def test_save_batch_returns_correct_count(self, db_with_schema):
        repo = DuckDBEnrichedPostRepository(db_with_schema)
        posts = [_make_enriched_post() for _ in range(3)]
        inserted = repo.save_batch(posts)
        assert inserted == 3

    def test_save_batch_empty_returns_zero(self, db_with_schema):
        repo = DuckDBEnrichedPostRepository(db_with_schema)
        assert repo.save_batch([]) == 0

    def test_save_batch_duplicate_returns_zero(self, db_with_schema):
        repo = DuckDBEnrichedPostRepository(db_with_schema)
        post = _make_enriched_post()
        assert repo.save_batch([post]) == 1
        assert repo.save_batch([post]) == 0

    def test_get_by_bronze_post_id_returns_saved_entity(self, db_with_schema):
        repo = DuckDBEnrichedPostRepository(db_with_schema)
        post = _make_enriched_post()
        repo.save(post)

        found = repo.get_by_bronze_post_id(str(post.bronze_post_id))
        assert found is not None
        assert found.id == post.id

    def test_get_by_bronze_post_id_returns_none_for_nonexistent(self, db_with_schema):
        repo = DuckDBEnrichedPostRepository(db_with_schema)
        assert repo.get_by_bronze_post_id(str(uuid4())) is None

    def test_get_by_search_returns_filtered_results(self, db_with_schema):
        repo = DuckDBEnrichedPostRepository(db_with_schema)
        sr_id = uuid4()
        posts = [_make_enriched_post(search_request_id=sr_id) for _ in range(3)]
        repo.save_batch(posts)

        results = repo.get_by_search(str(sr_id))
        assert len(results) == 3

    def test_get_by_search_returns_empty_for_nonexistent(self, db_with_schema):
        repo = DuckDBEnrichedPostRepository(db_with_schema)
        results = repo.get_by_search(str(uuid4()))
        assert results == []

    def test_count_by_search_returns_correct_count(self, db_with_schema):
        repo = DuckDBEnrichedPostRepository(db_with_schema)
        sr_id = uuid4()
        posts = [_make_enriched_post(search_request_id=sr_id) for _ in range(5)]
        repo.save_batch(posts)

        assert repo.count_by_search(str(sr_id)) == 5

    def test_count_by_search_returns_zero_for_nonexistent(self, db_with_schema):
        repo = DuckDBEnrichedPostRepository(db_with_schema)
        assert repo.count_by_search(str(uuid4())) == 0

    def test_round_trip_all_fields_match(self, db_with_schema):
        repo = DuckDBEnrichedPostRepository(db_with_schema)
        post = _make_enriched_post(
            platform=Platform.TWITTER,
            platform_id="tweet_abc123",
            author_handle="johndoe",
            author_name="John Doe",
            post_text="Test post content",
            posted_at=datetime(2025, 3, 15, 14, 30, 0),
            like_count=42,
            share_count=7,
            reply_count=3,
            view_count=500,
            post_url="https://twitter.com/johndoe/status/abc",
            is_retweet=True,
            created_at=datetime(2025, 3, 15, 15, 0, 0),
        )
        repo.save(post)

        found = repo.get_by_bronze_post_id(str(post.bronze_post_id))
        assert found is not None
        assert found.id == post.id
        assert found.bronze_post_id == post.bronze_post_id
        assert found.search_request_id == post.search_request_id
        assert found.platform == post.platform
        assert found.platform_id == post.platform_id
        assert found.author_handle == post.author_handle
        assert found.author_name == post.author_name
        assert found.post_text == post.post_text
        assert found.posted_at == post.posted_at
        assert found.like_count == post.like_count
        assert found.share_count == post.share_count
        assert found.reply_count == post.reply_count
        assert found.view_count == post.view_count
        assert found.post_url == post.post_url
        assert found.is_retweet == post.is_retweet
        assert found.created_at == post.created_at

    def test_get_by_search_ordered_by_posted_at_desc(self, db_with_schema):
        repo = DuckDBEnrichedPostRepository(db_with_schema)
        sr_id = uuid4()
        base_time = datetime(2025, 1, 15, 10, 0, 0)
        post_earlier = _make_enriched_post(
            search_request_id=sr_id,
            posted_at=base_time,
            platform_id="old",
        )
        post_later = _make_enriched_post(
            search_request_id=sr_id,
            posted_at=base_time.replace(hour=12),
            platform_id="new",
        )
        repo.save_batch([post_earlier, post_later])

        results = repo.get_by_search(str(sr_id))
        assert len(results) == 2
        assert results[0].platform_id == "new"
        assert results[1].platform_id == "old"
