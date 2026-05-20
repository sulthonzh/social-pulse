from __future__ import annotations

from uuid import UUID

import duckdb
import structlog
from datetime import datetime

from src.domain.entities.crawl_run import CrawlRun
from src.domain.value_objects.crawl_status import CrawlStatus
from src.domain.value_objects.platform import Platform

logger = structlog.get_logger()

_COLUMNS = (
    "id, search_request_id, platform, status, "
    "posts_fetched, error_message, started_at, completed_at"
)


def _row_to_crawl_run(row: tuple[object, ...]) -> CrawlRun:
    raw_id, raw_sr_id, raw_platform, raw_status, raw_posts, raw_err, raw_started, raw_completed = row
    started = raw_started if isinstance(raw_started, datetime) else datetime.fromisoformat(str(raw_started))
    completed = raw_completed if raw_completed is None else (
        raw_completed if isinstance(raw_completed, datetime) else datetime.fromisoformat(str(raw_completed))
    )
    return CrawlRun(
        id=UUID(str(raw_id)),
        search_request_id=UUID(str(raw_sr_id)),
        platform=Platform(str(raw_platform)),
        status=CrawlStatus(str(raw_status)),
        posts_fetched=int(str(raw_posts)),
        error_message=str(raw_err) if raw_err is not None else None,
        started_at=started,
        completed_at=completed,
    )


class DuckDBCrawlRunRepository:

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def save(self, crawl_run: CrawlRun) -> CrawlRun:
        self._conn.execute(
            f"""
            INSERT INTO bronze.bronze_crawl_runs
                ({_COLUMNS})
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                str(crawl_run.id),
                str(crawl_run.search_request_id),
                crawl_run.platform.value,
                crawl_run.status.value,
                crawl_run.posts_fetched,
                crawl_run.error_message,
                crawl_run.started_at,
                crawl_run.completed_at,
            ],
        )
        logger.debug(
            "crawl_run.saved",
            crawl_run_id=str(crawl_run.id),
            platform=crawl_run.platform.value,
        )
        return crawl_run

    def get_by_id(self, crawl_run_id: str) -> CrawlRun | None:
        row = self._conn.execute(
            f"""
            SELECT {_COLUMNS}
            FROM bronze.bronze_crawl_runs
            WHERE id = ?
            """,
            [crawl_run_id],
        ).fetchone()
        if row is None:
            return None
        return _row_to_crawl_run(row)

    def get_by_search_request(self, search_request_id: str) -> list[CrawlRun]:
        rows = self._conn.execute(
            f"""
            SELECT {_COLUMNS}
            FROM bronze.bronze_crawl_runs
            WHERE search_request_id = ?
            ORDER BY started_at
            """,
            [search_request_id],
        ).fetchall()
        return [_row_to_crawl_run(row) for row in rows]

    def update_status(
        self,
        crawl_run_id: str,
        status: str,
        posts_fetched: int,
        error_message: str | None,
    ) -> None:
        terminal_statuses = {"completed", "failed"}
        if status in terminal_statuses:
            self._conn.execute(
                """
                UPDATE bronze.bronze_crawl_runs
                SET status = ?,
                    posts_fetched = ?,
                    error_message = ?,
                    completed_at = current_timestamp
                WHERE id = ?
                """,
                [status, posts_fetched, error_message, crawl_run_id],
            )
        else:
            self._conn.execute(
                """
                UPDATE bronze.bronze_crawl_runs
                SET status = ?,
                    posts_fetched = ?,
                    error_message = ?
                WHERE id = ?
                """,
                [status, posts_fetched, error_message, crawl_run_id],
            )
        logger.debug(
            "crawl_run.status_updated",
            crawl_run_id=crawl_run_id,
            status=status,
            posts_fetched=posts_fetched,
        )
