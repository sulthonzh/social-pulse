from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

import duckdb
import structlog

from src.domain.entities.raw_post import RawPost
from src.domain.value_objects.platform import Platform

logger = structlog.get_logger()

_TABLE = "bronze.bronze_posts"

_INSERT_COLUMNS = (
    "id, search_request_id, crawl_run_id, platform, platform_id, "
    "author_handle, raw_payload, fetched_at"
)

_SELECT_COLUMNS = _INSERT_COLUMNS


def _row_to_raw_post(row: tuple[object, ...]) -> RawPost:
    (
        raw_id,
        raw_sr_id,
        raw_cr_id,
        raw_platform,
        raw_platform_id,
        raw_author,
        raw_payload,
        raw_fetched,
    ) = row

    resolved_id: UUID = raw_id if isinstance(raw_id, UUID) else UUID(str(raw_id))
    resolved_sr_id: UUID = raw_sr_id if isinstance(raw_sr_id, UUID) else UUID(str(raw_sr_id))
    resolved_cr_id: UUID = raw_cr_id if isinstance(raw_cr_id, UUID) else UUID(str(raw_cr_id))
    resolved_fetched: datetime = (
        raw_fetched
        if isinstance(raw_fetched, datetime)
        else datetime.fromisoformat(str(raw_fetched))
    )

    payload: dict[str, object] | None = None
    if raw_payload is not None:
        payload = json.loads(str(raw_payload))

    return RawPost(
        id=resolved_id,
        search_request_id=resolved_sr_id,
        crawl_run_id=resolved_cr_id,
        platform=Platform(str(raw_platform)),
        platform_id=str(raw_platform_id) if raw_platform_id is not None else None,
        author_handle=str(raw_author) if raw_author is not None else None,
        raw_payload=payload,
        fetched_at=resolved_fetched,
    )


def _post_to_params(post: RawPost) -> tuple[object, ...]:
    payload_str = json.dumps(post.raw_payload) if post.raw_payload is not None else None
    return (
        str(post.id),
        str(post.search_request_id),
        str(post.crawl_run_id),
        post.platform.value,
        post.platform_id,
        post.author_handle,
        payload_str,
        post.fetched_at,
    )


class DuckDBPostRepository:

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def save_posts(self, posts: list[RawPost]) -> int:
        if not posts:
            return 0

        ids = [str(p.id) for p in posts]
        placeholders = ",".join(["?"] * len(ids))

        before_row = self._conn.execute(
            f"SELECT count(*) FROM {_TABLE} WHERE id IN ({placeholders})",
            ids,
        ).fetchone()
        count_before_int = int(str(before_row[0])) if before_row is not None else 0

        params = [_post_to_params(p) for p in posts]
        self._conn.executemany(
            f"""
            INSERT OR IGNORE INTO {_TABLE}
                ({_INSERT_COLUMNS})
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            params,
        )

        after_row = self._conn.execute(
            f"SELECT count(*) FROM {_TABLE} WHERE id IN ({placeholders})",
            ids,
        ).fetchone()
        count_after_int = int(str(after_row[0])) if after_row is not None else 0

        inserted = count_after_int - count_before_int
        logger.debug(
            "posts_saved",
            attempted=len(posts),
            inserted=inserted,
        )
        return inserted

    def get_posts_by_search(self, search_request_id: str) -> list[RawPost]:
        rows = self._conn.execute(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM {_TABLE}
            WHERE search_request_id = ?
            ORDER BY fetched_at DESC
            """,
            [search_request_id],
        ).fetchall()
        return [_row_to_raw_post(row) for row in rows]

    def get_posts_by_crawl_run(self, crawl_run_id: str) -> list[RawPost]:
        rows = self._conn.execute(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM {_TABLE}
            WHERE crawl_run_id = ?
            ORDER BY fetched_at DESC
            """,
            [crawl_run_id],
        ).fetchall()
        return [_row_to_raw_post(row) for row in rows]

    def count_posts_by_search(self, search_request_id: str) -> int:
        result_row = self._conn.execute(
            f"SELECT count(*) FROM {_TABLE} WHERE search_request_id = ?",
            [search_request_id],
        ).fetchone()
        return int(str(result_row[0])) if result_row is not None else 0
