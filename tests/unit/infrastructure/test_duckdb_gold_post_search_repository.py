from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from src.domain.entities.gold_post_search import GoldPostSearch
from src.domain.value_objects.platform import Platform
from src.infrastructure.persistence.duckdb_gold_post_search_repository import (
    DuckDBGoldPostSearchRepository,
)

if TYPE_CHECKING:
    import duckdb


def _make_gold_post(**overrides: object) -> GoldPostSearch:
    defaults: dict[str, object] = {
        "id": uuid4(),
        "search_request_id": uuid4(),
        "keyword": "python",
        "platform": Platform.TWITTER,
        "author_handle": "testuser",
        "author_name": "Test User",
        "post_text": "Hello world",
        "posted_at": datetime(2025, 1, 15, 10, 0, 0),
        "post_url": "https://twitter.com/test/status/123",
        "sentiment": "positive",
        "sentiment_confidence": 0.95,
        "topic_label": "technology",
        "language": "en",
        "hashtags": ["python", "data"],
        "mentions": ["@friend"],
        "like_count": 10,
        "share_count": 5,
        "reply_count": 3,
        "view_count": 100,
        "ai_version": 1,
        "created_at": datetime(2025, 1, 15, 12, 0, 0),
    }
    defaults.update(overrides)
    return GoldPostSearch.model_validate(defaults)


@pytest.mark.unit
class TestDuckDBGoldPostSearchRepository:
    def test_save_batch_returns_correct_count(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        posts = [_make_gold_post() for _ in range(3)]
        inserted = repo.save_batch(posts)
        assert inserted == 3

    def test_save_batch_empty_returns_zero(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        assert repo.save_batch([]) == 0

    def test_save_batch_duplicate_returns_zero(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        post = _make_gold_post()
        assert repo.save_batch([post]) == 1
        assert repo.save_batch([post]) == 0

    def test_get_by_keyword_returns_matching_results(
        self, db_with_schema: duckdb.DuckDBPyConnection
    ):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        sr_id = uuid4()
        posts = [_make_gold_post(keyword="python", search_request_id=sr_id) for _ in range(3)]
        other = _make_gold_post(keyword="java", search_request_id=uuid4())
        repo.save_batch([*posts, other])

        results = repo.get_by_keyword("python")
        assert len(results) == 3

    def test_get_by_keyword_returns_empty_for_nonexistent(
        self, db_with_schema: duckdb.DuckDBPyConnection
    ):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        assert repo.get_by_keyword("nonexistent") == []

    def test_count_by_keyword_returns_correct_count(
        self, db_with_schema: duckdb.DuckDBPyConnection
    ):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        posts = [_make_gold_post(keyword="python") for _ in range(5)]
        repo.save_batch(posts)
        assert repo.count_by_keyword("python") == 5

    def test_count_by_keyword_returns_zero_for_nonexistent(
        self, db_with_schema: duckdb.DuckDBPyConnection
    ):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        assert repo.count_by_keyword("nonexistent") == 0

    def test_get_sentiment_breakdown(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        posts = [
            _make_gold_post(keyword="python", sentiment="positive"),
            _make_gold_post(keyword="python", sentiment="positive"),
            _make_gold_post(keyword="python", sentiment="negative"),
        ]
        repo.save_batch(posts)

        breakdown = repo.get_sentiment_breakdown("python")
        assert len(breakdown) == 2
        by_sentiment = {b["sentiment"]: b["count"] for b in breakdown}
        assert by_sentiment["positive"] == 2
        assert by_sentiment["negative"] == 1

    def test_get_filtered_by_sentiment(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        posts = [
            _make_gold_post(keyword="python", sentiment="positive"),
            _make_gold_post(keyword="python", sentiment="negative"),
        ]
        repo.save_batch(posts)

        results = repo.get_filtered("python", sentiment="positive")
        assert len(results) == 1
        assert results[0].sentiment == "positive"

    def test_get_filtered_by_platform(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        posts = [
            _make_gold_post(keyword="python", platform=Platform.TWITTER),
            _make_gold_post(keyword="python", platform=Platform.FACEBOOK),
        ]
        repo.save_batch(posts)

        results = repo.get_filtered("python", platform="twitter")
        assert len(results) == 1
        assert results[0].platform == Platform.TWITTER

    def test_get_filtered_by_language(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        posts = [
            _make_gold_post(keyword="python", language="en"),
            _make_gold_post(keyword="python", language="id"),
        ]
        repo.save_batch(posts)

        results = repo.get_filtered("python", language="en")
        assert len(results) == 1
        assert results[0].language == "en"

    def test_get_by_search_request_returns_matching(
        self, db_with_schema: duckdb.DuckDBPyConnection
    ):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        sr_id = uuid4()
        posts = [_make_gold_post(search_request_id=sr_id) for _ in range(3)]
        repo.save_batch(posts)

        results = repo.get_by_search_request(str(sr_id))
        assert len(results) == 3

    def test_get_by_search_request_returns_empty_for_nonexistent(
        self, db_with_schema: duckdb.DuckDBPyConnection
    ):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        assert repo.get_by_search_request(str(uuid4())) == []

    def test_round_trip_all_fields_match(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        post = _make_gold_post(
            platform=Platform.TWITTER,
            author_handle="johndoe",
            author_name="John Doe",
            post_text="Test post content",
            posted_at=datetime(2025, 3, 15, 14, 30, 0),
            post_url="https://twitter.com/johndoe/status/abc",
            sentiment="positive",
            sentiment_confidence=0.92,
            topic_label="technology",
            language="en",
            hashtags=["python", "data"],
            mentions=["@friend"],
            like_count=42,
            share_count=7,
            reply_count=3,
            view_count=500,
            ai_version=1,
            created_at=datetime(2025, 3, 15, 15, 0, 0),
        )
        repo.save_batch([post])

        results = repo.get_by_keyword("python")
        assert len(results) == 1
        found = results[0]
        assert found.id == post.id
        assert found.search_request_id == post.search_request_id
        assert found.keyword == post.keyword
        assert found.platform == post.platform
        assert found.author_handle == post.author_handle
        assert found.author_name == post.author_name
        assert found.post_text == post.post_text
        assert found.posted_at == post.posted_at
        assert found.post_url == post.post_url
        assert found.sentiment == post.sentiment
        assert found.sentiment_confidence == pytest.approx(post.sentiment_confidence, abs=1e-6)
        assert found.topic_label == post.topic_label
        assert found.language == post.language
        assert found.hashtags == post.hashtags
        assert found.mentions == post.mentions
        assert found.like_count == post.like_count
        assert found.share_count == post.share_count
        assert found.reply_count == post.reply_count
        assert found.view_count == post.view_count
        assert found.ai_version == post.ai_version
        assert found.created_at == post.created_at

    def test_get_campaigns_returns_distinct_campaigns(
        self, db_with_schema: duckdb.DuckDBPyConnection
    ):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        sr_id = uuid4()
        posts = [
            _make_gold_post(search_request_id=sr_id, keyword="python", platform=Platform.TWITTER),
            _make_gold_post(search_request_id=sr_id, keyword="python", platform=Platform.TWITTER),
            _make_gold_post(search_request_id=uuid4(), keyword="java", platform=Platform.FACEBOOK),
        ]
        repo.save_batch(posts)

        campaigns = repo.get_campaigns()

        assert len(campaigns) == 2
        keywords = {c["keyword"] for c in campaigns}
        assert keywords == {"java", "python"}

    def test_get_campaigns_returns_correct_fields(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        sr_id = uuid4()
        posts = [
            _make_gold_post(search_request_id=sr_id, keyword="python", platform=Platform.TWITTER),
        ]
        repo.save_batch(posts)

        campaigns = repo.get_campaigns()

        assert len(campaigns) == 1
        c = campaigns[0]
        assert "id" in c
        assert "keyword" in c
        assert "platform" in c
        assert c["keyword"] == "python"
        assert c["platform"] == "twitter"

    def test_get_campaigns_returns_empty_when_no_posts(
        self, db_with_schema: duckdb.DuckDBPyConnection
    ):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)

        campaigns = repo.get_campaigns()

        assert campaigns == []

    def test_get_campaigns_orders_by_keyword(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        posts = [
            _make_gold_post(keyword="zebra", search_request_id=uuid4()),
            _make_gold_post(keyword="apple", search_request_id=uuid4()),
        ]
        repo.save_batch(posts)

        campaigns = repo.get_campaigns()

        assert campaigns[0]["keyword"] == "apple"
        assert campaigns[1]["keyword"] == "zebra"

    def test_search_posts_returns_all_with_no_filters(
        self, db_with_schema: duckdb.DuckDBPyConnection
    ):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        posts = [
            _make_gold_post(keyword="python"),
            _make_gold_post(keyword="java"),
            _make_gold_post(keyword="rust"),
        ]
        repo.save_batch(posts)

        results, total = repo.search_posts(
            keyword=None,
            sentiment=None,
            platform=None,
            start_date=None,
            end_date=None,
            offset=0,
            limit=10,
        )

        assert total == 3
        assert len(results) == 3

    def test_search_posts_filters_by_keyword_ilike(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        posts = [
            _make_gold_post(post_text="I love Python programming"),
            _make_gold_post(post_text="Java is great too"),
        ]
        repo.save_batch(posts)

        results, total = repo.search_posts(
            keyword="python",
            sentiment=None,
            platform=None,
            start_date=None,
            end_date=None,
            offset=0,
            limit=10,
        )

        assert total == 1
        assert len(results) == 1
        assert "Python" in results[0].post_text

    def test_search_posts_filters_by_sentiment(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        posts = [
            _make_gold_post(keyword="python", sentiment="positive"),
            _make_gold_post(keyword="python", sentiment="negative"),
        ]
        repo.save_batch(posts)

        results, total = repo.search_posts(
            keyword=None,
            sentiment="positive",
            platform=None,
            start_date=None,
            end_date=None,
            offset=0,
            limit=10,
        )

        assert total == 1
        assert results[0].sentiment == "positive"

    def test_search_posts_filters_by_platform(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        posts = [
            _make_gold_post(platform=Platform.TWITTER),
            _make_gold_post(platform=Platform.FACEBOOK),
        ]
        repo.save_batch(posts)

        results, total = repo.search_posts(
            keyword=None,
            sentiment=None,
            platform="twitter",
            start_date=None,
            end_date=None,
            offset=0,
            limit=10,
        )

        assert total == 1
        assert results[0].platform == Platform.TWITTER

    def test_search_posts_filters_by_date_range(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        posts = [
            _make_gold_post(posted_at=datetime(2025, 1, 15, 10, 0, 0)),
            _make_gold_post(posted_at=datetime(2025, 2, 15, 10, 0, 0)),
            _make_gold_post(posted_at=datetime(2025, 3, 15, 10, 0, 0)),
        ]
        repo.save_batch(posts)

        _, total = repo.search_posts(
            keyword=None,
            sentiment=None,
            platform=None,
            start_date=datetime(2025, 1, 1, 0, 0, 0),
            end_date=datetime(2025, 2, 28, 23, 59, 59),
            offset=0,
            limit=10,
        )

        assert total == 2

    def test_search_posts_paginates_results(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        posts = [_make_gold_post() for _ in range(5)]
        repo.save_batch(posts)

        results, total = repo.search_posts(
            keyword=None,
            sentiment=None,
            platform=None,
            start_date=None,
            end_date=None,
            offset=0,
            limit=2,
        )

        assert total == 5
        assert len(results) == 2

    def test_search_posts_offset_works(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        posts = [_make_gold_post() for _ in range(5)]
        repo.save_batch(posts)

        results, total = repo.search_posts(
            keyword=None,
            sentiment=None,
            platform=None,
            start_date=None,
            end_date=None,
            offset=3,
            limit=2,
        )

        assert total == 5
        assert len(results) == 2

    def test_search_posts_returns_empty_when_no_matches(
        self, db_with_schema: duckdb.DuckDBPyConnection
    ):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)

        results, total = repo.search_posts(
            keyword="nonexistent",
            sentiment=None,
            platform=None,
            start_date=None,
            end_date=None,
            offset=0,
            limit=10,
        )

        assert results == []
        assert total == 0

    def test_search_posts_combined_filters(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldPostSearchRepository(db_with_schema)
        posts = [
            _make_gold_post(
                keyword="python",
                platform=Platform.TWITTER,
                sentiment="positive",
                posted_at=datetime(2025, 1, 15, 10, 0, 0),
            ),
            _make_gold_post(
                keyword="python",
                platform=Platform.FACEBOOK,
                sentiment="positive",
                posted_at=datetime(2025, 1, 15, 10, 0, 0),
            ),
            _make_gold_post(
                keyword="python",
                platform=Platform.TWITTER,
                sentiment="negative",
                posted_at=datetime(2025, 1, 15, 10, 0, 0),
            ),
        ]
        repo.save_batch(posts)

        results, total = repo.search_posts(
            keyword=None,
            sentiment="positive",
            platform="twitter",
            start_date=datetime(2025, 1, 1, 0, 0, 0),
            end_date=datetime(2025, 1, 31, 23, 59, 59),
            offset=0,
            limit=10,
        )

        assert total == 1
        assert results[0].platform == Platform.TWITTER
        assert results[0].sentiment == "positive"
