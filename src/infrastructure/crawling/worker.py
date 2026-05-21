"""Background crawl worker for the SocialPulse Bronze layer.

Polls bronze.search_requests for pending requests and executes
IngestCrawlRun to crawl posts and persist them.

Usage:
    python -m src.infrastructure.crawling.worker
"""

from __future__ import annotations

import asyncio
import contextlib
import signal
from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from src.application.use_cases.ingest_crawl import IngestCrawlRun
from src.domain.entities.search_request import SearchRequest
from src.domain.value_objects.crawl_status import CrawlStatus
from src.domain.value_objects.platform import Platform
from src.infrastructure.crawling import create_crawler
from src.infrastructure.persistence.duckdb_crawl_run_repository import (
    DuckDBCrawlRunRepository,
)
from src.infrastructure.persistence.duckdb_post_repository import DuckDBPostRepository
from src.infrastructure.persistence.duckdb_search_request_repository import (
    DuckDBSearchRequestRepository,
)
from src.infrastructure.persistence.migrations import create_all_tables
from src.shared.config import settings

if TYPE_CHECKING:
    import duckdb

logger = structlog.get_logger()

_POLL_INTERVAL_SECONDS: int = 15
_BATCH_SIZE: int = 50

_PENDING_SQL = """
    SELECT id, keyword, start_date, end_date, platform, status,
           posts_found, created_at, updated_at
    FROM bronze.search_requests
    WHERE status = 'pending'
    ORDER BY created_at
    LIMIT ?
"""


def _row_to_search_request(row: tuple[object, ...]) -> SearchRequest:
    """Convert a DuckDB row to a SearchRequest entity."""
    (
        raw_id,
        raw_keyword,
        raw_start_date,
        raw_end_date,
        raw_platform,
        raw_status,
        raw_posts_found,
        raw_created_at,
        raw_updated_at,
    ) = row

    resolved_id: UUID = raw_id if isinstance(raw_id, UUID) else UUID(str(raw_id))
    resolved_start: date = (
        raw_start_date
        if isinstance(raw_start_date, date) and not isinstance(raw_start_date, datetime)
        else date.fromisoformat(str(raw_start_date))
    )
    resolved_end: date = (
        raw_end_date
        if isinstance(raw_end_date, date) and not isinstance(raw_end_date, datetime)
        else date.fromisoformat(str(raw_end_date))
    )
    resolved_created: datetime = (
        raw_created_at
        if isinstance(raw_created_at, datetime)
        else datetime.fromisoformat(str(raw_created_at))
    )
    resolved_updated: datetime = (
        raw_updated_at
        if isinstance(raw_updated_at, datetime)
        else datetime.fromisoformat(str(raw_updated_at))
    )

    return SearchRequest(
        id=resolved_id,
        keyword=str(raw_keyword),
        start_date=resolved_start,
        end_date=resolved_end,
        platform=Platform(str(raw_platform)),
        status=CrawlStatus(str(raw_status)),
        posts_found=int(str(raw_posts_found)),
        created_at=resolved_created,
        updated_at=resolved_updated,
    )


class CrawlWorker:
    """Polls for pending search requests and runs crawl ingestion."""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn
        self._shutdown_event = asyncio.Event()

        search_request_repo = DuckDBSearchRequestRepository(conn)
        crawl_run_repo = DuckDBCrawlRunRepository(conn)
        post_repo = DuckDBPostRepository(conn)

        self._use_case = IngestCrawlRun(
            search_request_repo=search_request_repo,
            crawl_run_repo=crawl_run_repo,
            post_repo=post_repo,
        )

        self._crawler = create_crawler()
        logger.info("crawl_worker_initialized", crawler_type=type(self._crawler).__name__)

    def _fetch_pending_requests(self) -> list[SearchRequest]:
        """Find search requests with status 'pending'."""
        rows = self._conn.execute(
            _PENDING_SQL,
            [_BATCH_SIZE],
        ).fetchall()
        return [_row_to_search_request(row) for row in rows]

    async def _process_request(self, request: SearchRequest) -> None:
        """Run crawl ingestion for a single request, catching errors."""
        request_id = str(request.id)
        logger.info("crawl_job_processing", request_id=request_id, keyword=request.keyword)
        try:
            result = await self._use_case.execute(request, self._crawler)
            logger.info(
                "crawl_job_completed",
                request_id=request_id,
                status=result.status,
                posts_fetched=result.posts_fetched,
            )
        except Exception:
            logger.exception("crawl_job_failed", request_id=request_id)

    async def _run_once(self) -> int:
        """Single poll iteration. Returns number of requests processed."""
        requests = self._fetch_pending_requests()
        if not requests:
            return 0

        logger.info("crawl_batch_started", pending_count=len(requests))
        for request in requests:
            if self._shutdown_event.is_set():
                break
            await self._process_request(request)
        return len(requests)

    async def run_forever(self) -> None:
        """Main loop: poll, process, sleep, repeat until shutdown."""
        logger.info(
            "crawl_worker_started",
            poll_interval=_POLL_INTERVAL_SECONDS,
            batch_size=_BATCH_SIZE,
        )
        while not self._shutdown_event.is_set():
            processed = await self._run_once()
            if processed == 0:
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=_POLL_INTERVAL_SECONDS,
                    )
        logger.info("crawl_worker_stopped")

    def request_shutdown(self) -> None:
        """Signal the worker to stop after current work completes."""
        self._shutdown_event.set()


async def run(conn: duckdb.DuckDBPyConnection) -> None:
    """Entry point: run migrations, wire up the worker, handle signals."""
    create_all_tables(conn)

    worker = CrawlWorker(conn)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            worker.request_shutdown,
        )

    await worker.run_forever()


async def main() -> None:
    """Create a DuckDB connection and start the crawl worker.

    Retries with exponential backoff when the database is locked
    by another process (e.g., the Streamlit app).
    """
    import time  # noqa: PLC0415

    import duckdb  # noqa: PLC0415

    max_retries = 5
    base_delay = 2.0

    for attempt in range(1, max_retries + 1):
        try:
            conn = duckdb.connect(settings.db_path)
            break
        except duckdb.IOException as exc:
            if "lock" not in str(exc).lower() or attempt == max_retries:
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "db_locked_retry",
                attempt=attempt,
                max_retries=max_retries,
                delay=delay,
            )
            time.sleep(delay)
    else:
        raise RuntimeError("Failed to acquire DuckDB lock after retries")

    try:
        await run(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
