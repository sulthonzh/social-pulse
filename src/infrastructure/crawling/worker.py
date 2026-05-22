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
from uuid import UUID

import duckdb  # noqa: TC002
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
    """Polls for pending search requests and runs crawl ingestion.

    Uses short-lived DuckDB connections per poll cycle to avoid holding
    a persistent write lock that would block concurrent API writes.
    """

    def __init__(self) -> None:
        self._shutdown_event = asyncio.Event()
        logger.info("crawl_worker_initialized")

    def _fetch_pending_requests(self, conn: duckdb.DuckDBPyConnection) -> list[SearchRequest]:
        rows = conn.execute(_PENDING_SQL, [_BATCH_SIZE]).fetchall()
        return [_row_to_search_request(row) for row in rows]

    async def _process_request(
        self, request: SearchRequest, conn: duckdb.DuckDBPyConnection
    ) -> None:
        request_id = str(request.id)
        logger.info(
            "crawl_job_processing",
            request_id=request_id,
            keyword=request.keyword,
            platform=request.platform,
        )
        try:
            use_case = IngestCrawlRun(
                search_request_repo=DuckDBSearchRequestRepository(conn),
                crawl_run_repo=DuckDBCrawlRunRepository(conn),
                post_repo=DuckDBPostRepository(conn),
            )
            crawler = create_crawler(platform=request.platform)
            result = await use_case.execute(request, crawler)
            logger.info(
                "crawl_job_completed",
                request_id=request_id,
                status=result.status,
                posts_fetched=result.posts_fetched,
            )
        except Exception:
            logger.exception("crawl_job_failed", request_id=request_id)

    async def _run_once(self) -> int:
        """Single poll iteration with its own DB connection.

        Opens a connection, processes pending requests, then closes it
        to release the DuckDB write lock before sleeping.
        """
        from src.shared.db_retry import connect_with_retry  # noqa: PLC0415

        conn = connect_with_retry()
        try:
            requests = self._fetch_pending_requests(conn)
            if not requests:
                return 0

            logger.info("crawl_batch_started", pending_count=len(requests))
            for request in requests:
                if self._shutdown_event.is_set():
                    break
                await self._process_request(request, conn)
            return len(requests)
        finally:
            conn.close()

    async def run_forever(self) -> None:
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
        self._shutdown_event.set()


async def run(conn: duckdb.DuckDBPyConnection) -> None:
    """Entry point: run migrations, wire up the worker, handle signals."""
    create_all_tables(conn)
    conn.close()

    worker = CrawlWorker()

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
    from src.shared.db_retry import connect_with_retry  # noqa: PLC0415

    conn: duckdb.DuckDBPyConnection = connect_with_retry()

    try:
        await run(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
