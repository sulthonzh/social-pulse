from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from src.domain.entities.search_request import SearchRequest
from src.domain.value_objects.crawl_status import CrawlStatus
from src.domain.value_objects.platform import Platform

if TYPE_CHECKING:
    import duckdb

logger = structlog.get_logger()

_TABLE = "bronze.search_requests"

_SELECT_COLUMNS = (
    "id, keyword, start_date, end_date, platform, status, posts_found, created_at, updated_at"
)


class DuckDBSearchRequestRepository:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def save(self, request: SearchRequest) -> SearchRequest:
        logger.debug("saving_search_request", keyword=request.keyword)
        self._conn.execute(
            f"""
            INSERT INTO {_TABLE}
                (id, keyword, start_date, end_date, platform, status,
                 posts_found, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                request.id,
                request.keyword,
                request.start_date,
                request.end_date,
                request.platform.value,
                request.status.value,
                request.posts_found,
                request.created_at,
                request.updated_at,
            ],
        )
        logger.debug(
            "search_request_saved",
            request_id=str(request.id),
            keyword=request.keyword,
        )
        return request

    def get_by_id(self, request_id: str) -> SearchRequest | None:
        logger.debug("fetching_search_request_by_id", request_id=request_id)
        row = self._conn.execute(
            f"SELECT {_SELECT_COLUMNS} FROM {_TABLE} WHERE id = ?",
            [request_id],
        ).fetchone()
        if row is None:
            return None
        return self._row_to_entity(row)

    def get_by_keyword(self, keyword: str) -> list[SearchRequest]:
        logger.debug("fetching_search_requests_by_keyword", keyword=keyword)
        rows = self._conn.execute(
            f"SELECT {_SELECT_COLUMNS} FROM {_TABLE} WHERE keyword = ?",
            [keyword],
        ).fetchall()
        return [self._row_to_entity(row) for row in rows]

    def update_status(self, request_id: str, status: str, posts_found: int) -> None:
        logger.debug(
            "updating_search_request_status",
            request_id=request_id,
            status=status,
            posts_found=posts_found,
        )
        self._conn.execute(
            f"""
            UPDATE {_TABLE}
            SET status = ?,
                posts_found = ?,
                updated_at = current_timestamp
            WHERE id = ?
            """,
            [status, posts_found, request_id],
        )

    @staticmethod
    def _row_to_entity(row: tuple[object, ...]) -> SearchRequest:
        (
            id_val,
            keyword,
            start_date_val,
            end_date_val,
            platform_val,
            status_val,
            posts_found,
            created_at_val,
            updated_at_val,
        ) = row

        resolved_id: UUID = id_val if isinstance(id_val, UUID) else UUID(str(id_val))
        resolved_start: date = (
            start_date_val
            if isinstance(start_date_val, date) and not isinstance(start_date_val, datetime)
            else date.fromisoformat(str(start_date_val))
        )
        resolved_end: date = (
            end_date_val
            if isinstance(end_date_val, date) and not isinstance(end_date_val, datetime)
            else date.fromisoformat(str(end_date_val))
        )
        resolved_created: datetime = (
            created_at_val
            if isinstance(created_at_val, datetime)
            else datetime.fromisoformat(str(created_at_val))
        )
        resolved_updated: datetime = (
            updated_at_val
            if isinstance(updated_at_val, datetime)
            else datetime.fromisoformat(str(updated_at_val))
        )

        return SearchRequest(
            id=resolved_id,
            keyword=str(keyword),
            start_date=resolved_start,
            end_date=resolved_end,
            platform=Platform(str(platform_val)),
            status=CrawlStatus(str(status_val)),
            posts_found=int(str(posts_found)),
            created_at=resolved_created,
            updated_at=resolved_updated,
        )
