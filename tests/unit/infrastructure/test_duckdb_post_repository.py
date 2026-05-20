from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from src.domain.entities.crawl_run import CrawlRun
from src.domain.entities.raw_post import RawPost
from src.domain.entities.search_request import SearchRequest
from src.domain.value_objects.crawl_status import CrawlStatus
from src.domain.value_objects.platform import Platform
from src.infrastructure.persistence.duckdb_crawl_run_repository import (
    DuckDBCrawlRunRepository,
)
from src.infrastructure.persistence.duckdb_post_repository import DuckDBPostRepository
from src.infrastructure.persistence.duckdb_search_request_repository import (
    DuckDBSearchRequestRepository,
)


def _make_search_request() -> SearchRequest:
    return SearchRequest(
        id=uuid4(),
        keyword="python",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
        platform=Platform.TWITTER,
        status=CrawlStatus.PENDING,
        posts_found=0,
        created_at=datetime(2025, 1, 1, 0, 0, 0),
        updated_at=datetime(2025, 1, 1, 0, 0, 0),
    )


def _make_crawl_run(search_request_id: UUID) -> CrawlRun:
    return CrawlRun(
        id=uuid4(),
        search_request_id=search_request_id,
        platform=Platform.TWITTER,
        status=CrawlStatus.RUNNING,
        posts_fetched=0,
        started_at=datetime(2025, 1, 1, 12, 0, 0),
    )


def _insert_prerequisites(db_with_schema):
    """Insert a SearchRequest and CrawlRun so FK constraints pass."""
    sr_repo = DuckDBSearchRequestRepository(db_with_schema)
    cr_repo = DuckDBCrawlRunRepository(db_with_schema)

    sr = _make_search_request()
    sr_repo.save(sr)
    cr = _make_crawl_run(sr.id)
    cr_repo.save(cr)
    return sr, cr


def _make_post(
    search_request_id, crawl_run_id, *, platform_id=None, fetched_at=None
):
    return RawPost(
        id=uuid4(),
        search_request_id=search_request_id,
        crawl_run_id=crawl_run_id,
        platform=Platform.TWITTER,
        platform_id=platform_id or f"tweet_{uuid4().hex[:8]}",
        author_handle="testuser",
        raw_payload={"text": "hello world", "likes": 42},
        fetched_at=fetched_at or datetime(2025, 1, 15, 10, 0, 0),
    )


@pytest.mark.unit
class TestDuckDBPostRepository:

    def test_save_posts_empty_list_returns_zero(self, db_with_schema):
        repo = DuckDBPostRepository(db_with_schema)
        assert repo.save_posts([]) == 0

    def test_save_posts_multiple_returns_correct_count(self, db_with_schema):
        sr, cr = _insert_prerequisites(db_with_schema)
        repo = DuckDBPostRepository(db_with_schema)

        posts = [_make_post(sr.id, cr.id) for _ in range(3)]
        inserted = repo.save_posts(posts)
        assert inserted == 3

    def test_save_posts_duplicate_returns_zero(self, db_with_schema):
        sr, cr = _insert_prerequisites(db_with_schema)
        repo = DuckDBPostRepository(db_with_schema)

        post = _make_post(sr.id, cr.id)
        assert repo.save_posts([post]) == 1
        assert repo.save_posts([post]) == 0

    def test_get_posts_by_search_returns_filtered(self, db_with_schema):
        sr, cr = _insert_prerequisites(db_with_schema)
        repo = DuckDBPostRepository(db_with_schema)

        posts = [_make_post(sr.id, cr.id) for _ in range(2)]
        repo.save_posts(posts)

        results = repo.get_posts_by_search(str(sr.id))
        assert len(results) == 2

    def test_get_posts_by_search_nonexistent_returns_empty(self, db_with_schema):
        repo = DuckDBPostRepository(db_with_schema)
        results = repo.get_posts_by_search(str(uuid4()))
        assert results == []

    def test_get_posts_by_crawl_run_returns_filtered(self, db_with_schema):
        sr, cr = _insert_prerequisites(db_with_schema)
        repo = DuckDBPostRepository(db_with_schema)

        posts = [_make_post(sr.id, cr.id) for _ in range(3)]
        repo.save_posts(posts)

        results = repo.get_posts_by_crawl_run(str(cr.id))
        assert len(results) == 3

    def test_get_posts_by_crawl_run_nonexistent_returns_empty(self, db_with_schema):
        repo = DuckDBPostRepository(db_with_schema)
        results = repo.get_posts_by_crawl_run(str(uuid4()))
        assert results == []

    def test_count_posts_by_search_returns_correct_count(self, db_with_schema):
        sr, cr = _insert_prerequisites(db_with_schema)
        repo = DuckDBPostRepository(db_with_schema)

        posts = [_make_post(sr.id, cr.id) for _ in range(5)]
        repo.save_posts(posts)

        assert repo.count_posts_by_search(str(sr.id)) == 5

    def test_count_posts_by_search_nonexistent_returns_zero(self, db_with_schema):
        repo = DuckDBPostRepository(db_with_schema)
        assert repo.count_posts_by_search(str(uuid4())) == 0

    def test_raw_payload_round_trip(self, db_with_schema):
        sr, cr = _insert_prerequisites(db_with_schema)
        repo = DuckDBPostRepository(db_with_schema)

        payload = {
            "text": "test post",
            "metrics": {"likes": 10, "retweets": 3},
            "tags": ["python", "data"],
        }
        post = _make_post(sr.id, cr.id)
        post = RawPost(
            id=post.id,
            search_request_id=post.search_request_id,
            crawl_run_id=post.crawl_run_id,
            platform=post.platform,
            platform_id=post.platform_id,
            author_handle=post.author_handle,
            raw_payload=payload,
            fetched_at=post.fetched_at,
        )
        repo.save_posts([post])

        results = repo.get_posts_by_search(str(sr.id))
        assert len(results) == 1
        assert results[0].raw_payload == payload

    def test_posts_ordered_by_fetched_at_desc(self, db_with_schema):
        sr, cr = _insert_prerequisites(db_with_schema)
        repo = DuckDBPostRepository(db_with_schema)

        base_time = datetime(2025, 1, 15, 10, 0, 0)
        post_earlier = _make_post(
            sr.id, cr.id, fetched_at=base_time, platform_id="old"
        )
        post_later = _make_post(
            sr.id,
            cr.id,
            fetched_at=base_time + timedelta(hours=2),
            platform_id="new",
        )
        repo.save_posts([post_earlier, post_later])

        results = repo.get_posts_by_search(str(sr.id))
        assert len(results) == 2
        assert results[0].platform_id == "new"
        assert results[1].platform_id == "old"
