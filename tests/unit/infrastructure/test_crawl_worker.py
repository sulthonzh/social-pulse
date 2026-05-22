from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from src.domain.entities.crawl_run import CrawlRun
from src.domain.entities.search_request import SearchRequest
from src.domain.value_objects.crawl_status import CrawlStatus
from src.domain.value_objects.platform import Platform
from src.infrastructure.crawling.worker import (
    CrawlWorker,
    _row_to_search_request,
)


def _make_request(
    keyword: str = "python",
    start_date: date = date(2025, 1, 1),
    end_date: date = date(2025, 1, 31),
    platform: Platform = Platform.TWITTER,
    status: CrawlStatus = CrawlStatus.PENDING,
) -> SearchRequest:
    return SearchRequest(
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
        platform=platform,
        status=status,
    )


def _make_row(request: SearchRequest) -> tuple[object, ...]:
    return (
        request.id,
        request.keyword,
        request.start_date,
        request.end_date,
        request.platform.value,
        request.status.value,
        request.posts_found,
        request.created_at,
        request.updated_at,
    )


def _mock_conn_with_rows(rows: list[tuple[object, ...]]) -> MagicMock:
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    conn.execute.return_value = cursor
    return conn


def _mock_use_case(return_value: CrawlRun | None = None) -> AsyncMock:
    if return_value is None:
        return_value = CrawlRun(
            search_request_id=uuid4(),
            platform=Platform.TWITTER,
            status=CrawlStatus.COMPLETED,
            posts_fetched=3,
        )
    use_case = AsyncMock()
    use_case.execute.return_value = return_value
    return use_case


@pytest.mark.unit
class TestRowToSearchRequest:
    def test_converts_full_row_with_native_types(self):
        request = _make_request()
        row = _make_row(request)
        result = _row_to_search_request(row)

        assert result.id == request.id
        assert result.keyword == request.keyword
        assert result.start_date == request.start_date
        assert result.end_date == request.end_date
        assert result.platform == request.platform
        assert result.status == request.status
        assert result.posts_found == request.posts_found

    def test_converts_row_with_string_types(self):
        uid = uuid4()
        row = (
            str(uid),
            "test",
            "2025-02-01",
            "2025-02-28",
            "twitter",
            "pending",
            "0",
            "2025-02-01T00:00:00+00:00",
            "2025-02-01T00:00:00+00:00",
        )
        result = _row_to_search_request(row)

        assert result.id == uid
        assert result.keyword == "test"
        assert result.start_date == date(2025, 2, 1)
        assert result.end_date == date(2025, 2, 28)
        assert result.platform == Platform.TWITTER
        assert result.status == CrawlStatus.PENDING


@pytest.mark.unit
class TestCrawlWorkerFetchPending:
    async def test_fetches_pending_requests(self):
        request = _make_request()
        conn = _mock_conn_with_rows([_make_row(request)])

        worker = CrawlWorker()
        results = worker._fetch_pending_requests(conn)
        assert len(results) == 1
        assert results[0].keyword == "python"

    async def test_returns_empty_when_no_pending(self):
        conn = _mock_conn_with_rows([])

        worker = CrawlWorker()
        results = worker._fetch_pending_requests(conn)
        assert results == []


@pytest.mark.unit
class TestCrawlWorkerProcessRequest:
    async def test_calls_use_case_for_each_request(self):
        request = _make_request()
        crawl_run = CrawlRun(
            search_request_id=request.id,
            platform=Platform.TWITTER,
            status=CrawlStatus.COMPLETED,
            posts_fetched=5,
        )
        use_case = _mock_use_case(return_value=crawl_run)
        conn = _mock_conn_with_rows([])

        with (
            patch("src.infrastructure.crawling.worker.create_crawler") as mock_crawler,
            patch(
                "src.infrastructure.crawling.worker.IngestCrawlRun",
                return_value=use_case,
            ),
        ):
            mock_crawler.return_value = MagicMock()
            worker = CrawlWorker()
            await worker._process_request(request, conn)

        use_case.execute.assert_awaited_once()
        args = use_case.execute.call_args
        assert args[0][0] == request

    async def test_handles_crawl_failure_without_crashing(self):
        request = _make_request()
        use_case = _mock_use_case()
        use_case.execute.side_effect = RuntimeError("Crawl API down")
        conn = _mock_conn_with_rows([])

        with (
            patch("src.infrastructure.crawling.worker.create_crawler") as mock_crawler,
            patch(
                "src.infrastructure.crawling.worker.IngestCrawlRun",
                return_value=use_case,
            ),
        ):
            mock_crawler.return_value = MagicMock()
            worker = CrawlWorker()
            await worker._process_request(request, conn)

        use_case.execute.assert_awaited_once()


@pytest.mark.unit
class TestCrawlWorkerRunOnce:
    async def test_processes_all_pending_requests(self):
        r1 = _make_request(keyword="python")
        r2 = _make_request(keyword="rust")
        conn = _mock_conn_with_rows([_make_row(r1), _make_row(r2)])
        use_case = _mock_use_case()

        with (
            patch("src.infrastructure.crawling.worker.create_crawler") as mock_crawler,
            patch(
                "src.infrastructure.crawling.worker.IngestCrawlRun",
                return_value=use_case,
            ),
            patch("duckdb.connect", return_value=conn),
        ):
            mock_crawler.return_value = MagicMock()
            worker = CrawlWorker()

            processed = await worker._run_once()
            assert processed == 2
            assert use_case.execute.await_count == 2

    async def test_returns_zero_when_no_pending(self):
        conn = _mock_conn_with_rows([])
        use_case = _mock_use_case()

        with (
            patch("src.infrastructure.crawling.worker.create_crawler") as mock_crawler,
            patch(
                "src.infrastructure.crawling.worker.IngestCrawlRun",
                return_value=use_case,
            ),
            patch("duckdb.connect", return_value=conn),
        ):
            mock_crawler.return_value = MagicMock()
            worker = CrawlWorker()

            processed = await worker._run_once()
            assert processed == 0
            use_case.execute.assert_not_awaited()

    async def test_stops_on_shutdown_mid_batch(self):
        r1 = _make_request(keyword="python")
        r2 = _make_request(keyword="rust")
        conn = _mock_conn_with_rows([_make_row(r1), _make_row(r2)])
        use_case = _mock_use_case()

        with (
            patch("src.infrastructure.crawling.worker.create_crawler") as mock_crawler,
            patch(
                "src.infrastructure.crawling.worker.IngestCrawlRun",
                return_value=use_case,
            ),
            patch("duckdb.connect", return_value=conn),
        ):
            mock_crawler.return_value = MagicMock()
            worker = CrawlWorker()

            worker.request_shutdown()
            processed = await worker._run_once()
            assert processed == 2
            assert use_case.execute.await_count <= 2


@pytest.mark.unit
class TestCrawlWorkerShutdown:
    async def test_shutdown_event_stops_loop(self):
        conn = _mock_conn_with_rows([])
        use_case = _mock_use_case()

        with (
            patch("src.infrastructure.crawling.worker.create_crawler") as mock_crawler,
            patch(
                "src.infrastructure.crawling.worker.IngestCrawlRun",
                return_value=use_case,
            ),
            patch("duckdb.connect", return_value=conn),
        ):
            mock_crawler.return_value = MagicMock()
            worker = CrawlWorker()

            worker.request_shutdown()
            assert worker._shutdown_event.is_set()

            await worker.run_forever()

    async def test_empty_pending_sleeps_then_shutdown(self):
        conn = _mock_conn_with_rows([])
        use_case = _mock_use_case()

        with (
            patch("src.infrastructure.crawling.worker.create_crawler") as mock_crawler,
            patch(
                "src.infrastructure.crawling.worker.IngestCrawlRun",
                return_value=use_case,
            ),
            patch("duckdb.connect", return_value=conn),
        ):
            mock_crawler.return_value = MagicMock()
            worker = CrawlWorker()

            import asyncio  # noqa: PLC0415

            async def shutdown_soon():
                await asyncio.sleep(0.05)
                worker.request_shutdown()

            await asyncio.gather(worker.run_forever(), shutdown_soon())
