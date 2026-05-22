from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.domain.entities.crawl_run import CrawlRun
from src.domain.entities.search_request import SearchRequest
from src.domain.value_objects.crawl_status import CrawlStatus
from src.domain.value_objects.platform import Platform
from src.infrastructure.crawling.worker import CrawlWorker
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


@pytest.mark.integration
async def test_worker_fetches_pending_requests_from_db(db_with_schema):
    repo = DuckDBSearchRequestRepository(db_with_schema)
    repo.save(_make_request(keyword="python"))

    worker = CrawlWorker()
    pending = worker._fetch_pending_requests(db_with_schema)
    assert len(pending) == 1
    assert pending[0].keyword == "python"
    assert pending[0].status == CrawlStatus.PENDING


@pytest.mark.integration
async def test_worker_skips_non_pending_requests(db_with_schema):
    request = _make_request()
    repo = DuckDBSearchRequestRepository(db_with_schema)
    saved = repo.save(request)
    repo.update_status(str(saved.id), "completed", 10)

    worker = CrawlWorker()
    pending = worker._fetch_pending_requests(db_with_schema)
    assert len(pending) == 0


@pytest.mark.integration
async def test_worker_processes_request_end_to_end(db_with_schema):
    request = _make_request(keyword="python")

    use_case = AsyncMock()
    use_case.execute.return_value = CrawlRun(
        search_request_id=request.id,
        platform=Platform.TWITTER,
        status=CrawlStatus.COMPLETED,
        posts_fetched=5,
    )

    mock_crawler = MagicMock()

    with (
        patch("src.infrastructure.crawling.worker.create_crawler") as mock_crawler_fn,
        patch(
            "src.infrastructure.crawling.worker.IngestCrawlRun",
            return_value=use_case,
        ),
        patch("duckdb.connect", return_value=db_with_schema),
    ):
        mock_crawler_fn.return_value = mock_crawler

        worker = CrawlWorker()
        repo = DuckDBSearchRequestRepository(db_with_schema)
        repo.save(request)

        processed = await worker._run_once()
        assert processed == 1

        use_case.execute.assert_awaited_once()
        called_request, called_crawler = use_case.execute.call_args[0]
        assert called_request.keyword == "python"
        assert called_crawler is mock_crawler


@pytest.mark.integration
async def test_worker_handles_multiple_pending_requests(db_with_schema):
    repo = DuckDBSearchRequestRepository(db_with_schema)
    r1 = _make_request(keyword="python")
    r2 = _make_request(keyword="rust")
    r3 = _make_request(keyword="golang")
    repo.save(r1)
    repo.save(r2)
    repo.save(r3)

    use_case = AsyncMock()
    use_case.execute.return_value = CrawlRun(
        search_request_id=r1.id,
        platform=Platform.TWITTER,
        status=CrawlStatus.COMPLETED,
        posts_fetched=3,
    )

    mock_crawler = MagicMock()

    with (
        patch("src.infrastructure.crawling.worker.create_crawler") as mock_crawler_fn,
        patch(
            "src.infrastructure.crawling.worker.IngestCrawlRun",
            return_value=use_case,
        ),
        patch("duckdb.connect", return_value=db_with_schema),
    ):
        mock_crawler_fn.return_value = mock_crawler

        worker = CrawlWorker()
        processed = await worker._run_once()
        assert processed == 3
        assert use_case.execute.await_count == 3
