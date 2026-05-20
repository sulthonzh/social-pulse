from __future__ import annotations

import json
from datetime import date, datetime
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from src.application.use_cases.ingest_crawl import IngestCrawlRun
from src.domain.entities.raw_post import RawPost
from src.domain.entities.search_request import SearchRequest
from src.domain.exceptions import CrawlError
from src.domain.value_objects.crawl_status import CrawlStatus
from src.domain.value_objects.platform import Platform
from src.infrastructure.persistence.duckdb_crawl_run_repository import (
    DuckDBCrawlRunRepository,
)
from src.infrastructure.persistence.duckdb_post_repository import DuckDBPostRepository
from src.infrastructure.persistence.duckdb_search_request_repository import (
    DuckDBSearchRequestRepository,
)


def _make_request(
    keyword: str = "python",
    start_date: date = date(2025, 1, 1),
    end_date: date = date(2025, 1, 31),
    platform: Platform = Platform.TWITTER,
) -> SearchRequest:
    return SearchRequest(
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
        platform=platform,
    )


def _make_post(
    idx: int,
    platform: Platform = Platform.TWITTER,
    platform_id: str | None = None,
) -> RawPost:
    pid = platform_id or f"post-{idx}"
    return RawPost(
        search_request_id=uuid4(),
        crawl_run_id=uuid4(),
        platform=platform,
        platform_id=pid,
        author_handle=f"user_{idx}",
        raw_payload={"text": f"post content {idx}", "index": idx},
    )


def _build_use_case(db_with_schema):
    post_repo = DuckDBPostRepository(db_with_schema)
    search_request_repo = DuckDBSearchRequestRepository(db_with_schema)
    crawl_run_repo = DuckDBCrawlRunRepository(db_with_schema)

    use_case = IngestCrawlRun(
        search_request_repo=search_request_repo,
        crawl_run_repo=crawl_run_repo,
        post_repo=post_repo,
    )
    return use_case


def _make_crawler(return_value=None, side_effect=None):
    crawler = AsyncMock()
    if side_effect is not None:
        crawler.crawl.side_effect = side_effect
    else:
        crawler.crawl.return_value = return_value if return_value is not None else []
    return crawler


@pytest.mark.integration
async def test_full_happy_path_pipeline(db_with_schema):
    posts = [_make_post(i) for i in range(5)]
    crawler = _make_crawler(return_value=posts)
    use_case = _build_use_case(db_with_schema)
    request = _make_request()

    result = await use_case.execute(request, crawler)

    assert result.status == CrawlStatus.COMPLETED
    assert result.posts_fetched == 5

    sr_row = db_with_schema.execute(
        "SELECT status, posts_found FROM bronze.search_requests WHERE id = ?",
        [str(result.search_request_id)],
    ).fetchone()
    assert sr_row is not None
    assert sr_row[0] == "completed"
    assert sr_row[1] == 5

    cr_row = db_with_schema.execute(
        "SELECT status, posts_fetched FROM bronze.bronze_crawl_runs WHERE id = ?",
        [str(result.id)],
    ).fetchone()
    assert cr_row is not None
    assert cr_row[0] == "completed"
    assert cr_row[1] == 5

    post_rows = db_with_schema.execute(
        "SELECT id, search_request_id, crawl_run_id, raw_payload "
        "FROM bronze.bronze_posts "
        "WHERE search_request_id = ? AND crawl_run_id = ?",
        [str(result.search_request_id), str(result.id)],
    ).fetchall()
    assert len(post_rows) == 5

    for row in post_rows:
        payload = json.loads(str(row[3]))
        assert "text" in payload
        assert "index" in payload


@pytest.mark.integration
async def test_pipeline_with_crawler_failure(db_with_schema):
    crawler = _make_crawler(side_effect=CrawlError("API rate limit"))
    use_case = _build_use_case(db_with_schema)
    request = _make_request()

    with pytest.raises(CrawlError, match="API rate limit"):
        await use_case.execute(request, crawler)

    sr_row = db_with_schema.execute(
        "SELECT status, posts_found FROM bronze.search_requests "
        "ORDER BY created_at DESC LIMIT 1",
    ).fetchone()
    assert sr_row is not None
    assert sr_row[0] == "failed"
    assert sr_row[1] == 0

    cr_row = db_with_schema.execute(
        "SELECT status, error_message FROM bronze.bronze_crawl_runs "
        "ORDER BY started_at DESC LIMIT 1",
    ).fetchone()
    assert cr_row is not None
    assert cr_row[0] == "failed"
    assert "API rate limit" in str(cr_row[1])

    post_count = db_with_schema.execute(
        "SELECT count(*) FROM bronze.bronze_posts",
    ).fetchone()
    assert post_count is not None
    assert post_count[0] == 0


@pytest.mark.integration
async def test_pipeline_with_empty_crawl_results(db_with_schema):
    crawler = _make_crawler(return_value=[])
    use_case = _build_use_case(db_with_schema)
    request = _make_request()

    result = await use_case.execute(request, crawler)

    assert result.status == CrawlStatus.COMPLETED
    assert result.posts_fetched == 0

    sr_row = db_with_schema.execute(
        "SELECT status, posts_found FROM bronze.search_requests "
        "ORDER BY created_at DESC LIMIT 1",
    ).fetchone()
    assert sr_row is not None
    assert sr_row[0] == "completed"
    assert sr_row[1] == 0

    post_count = db_with_schema.execute(
        "SELECT count(*) FROM bronze.bronze_posts",
    ).fetchone()
    assert post_count is not None
    assert post_count[0] == 0


@pytest.mark.integration
async def test_pipeline_with_duplicate_posts_idempotency(db_with_schema):
    posts = [
        _make_post(0, platform_id="dup-1"),
        _make_post(1, platform_id="dup-1"),
        _make_post(2, platform_id="unique-2"),
    ]
    assert posts[0].platform_id == posts[1].platform_id
    assert posts[0].platform == posts[1].platform

    crawler = _make_crawler(return_value=posts)
    use_case = _build_use_case(db_with_schema)
    request = _make_request()

    result = await use_case.execute(request, crawler)

    assert result.status == CrawlStatus.COMPLETED
    assert result.posts_fetched == 2

    post_rows = db_with_schema.execute(
        "SELECT platform_id FROM bronze.bronze_posts "
        "WHERE search_request_id = ?",
        [str(result.search_request_id)],
    ).fetchall()
    assert len(post_rows) == 2
    platform_ids = sorted(row[0] for row in post_rows)
    assert platform_ids == ["dup-1", "unique-2"]
