from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from src.domain.entities.enriched_post import EnrichedPost
from src.domain.value_objects.platform import Platform

if TYPE_CHECKING:
    import duckdb

logger = structlog.get_logger()

_TABLE = "silver.silver_posts"

_INSERT_COLUMNS = (
    "id, bronze_post_id, search_request_id, platform, platform_id, "
    "author_handle, author_name, post_text, posted_at, "
    "like_count, share_count, reply_count, view_count, "
    "post_url, is_retweet, created_at"
)

_SELECT_COLUMNS = _INSERT_COLUMNS


def _resolve_uuid(raw: object) -> UUID:
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def _resolve_datetime(raw: object) -> datetime | None:
    if raw is None:
        return None
    return raw if isinstance(raw, datetime) else datetime.fromisoformat(str(raw))


def _row_to_enriched_post(row: tuple[object, ...]) -> EnrichedPost:
    (
        raw_id,
        raw_bronze_id,
        raw_sr_id,
        raw_platform,
        raw_platform_id,
        raw_author_handle,
        raw_author_name,
        raw_post_text,
        raw_posted_at,
        raw_like_count,
        raw_share_count,
        raw_reply_count,
        raw_view_count,
        raw_post_url,
        raw_is_retweet,
        raw_created_at,
    ) = row

    return EnrichedPost(
        id=_resolve_uuid(raw_id),
        bronze_post_id=_resolve_uuid(raw_bronze_id),
        search_request_id=_resolve_uuid(raw_sr_id),
        platform=Platform(str(raw_platform)),
        platform_id=str(raw_platform_id) if raw_platform_id is not None else None,
        author_handle=str(raw_author_handle) if raw_author_handle is not None else None,
        author_name=str(raw_author_name) if raw_author_name is not None else None,
        post_text=str(raw_post_text) if raw_post_text is not None else None,
        posted_at=_resolve_datetime(raw_posted_at),
        like_count=int(str(raw_like_count)),
        share_count=int(str(raw_share_count)),
        reply_count=int(str(raw_reply_count)),
        view_count=int(str(raw_view_count)),
        post_url=str(raw_post_url) if raw_post_url is not None else None,
        is_retweet=bool(raw_is_retweet),
        created_at=_resolve_datetime(raw_created_at) or datetime.now(),
    )


def _post_to_params(post: EnrichedPost) -> tuple[object, ...]:
    return (
        str(post.id),
        str(post.bronze_post_id),
        str(post.search_request_id),
        post.platform.value,
        post.platform_id,
        post.author_handle,
        post.author_name,
        post.post_text,
        post.posted_at,
        post.like_count,
        post.share_count,
        post.reply_count,
        post.view_count,
        post.post_url,
        post.is_retweet,
        post.created_at,
    )


class DuckDBEnrichedPostRepository:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def save(self, post: EnrichedPost) -> EnrichedPost:
        self._conn.execute(
            f"""
            INSERT OR IGNORE INTO {_TABLE}
                ({_INSERT_COLUMNS})
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            list(_post_to_params(post)),
        )
        logger.debug(
            "enriched_post.saved",
            post_id=str(post.id),
            bronze_post_id=str(post.bronze_post_id),
        )
        return post

    def save_batch(self, posts: list[EnrichedPost]) -> int:
        if not posts:
            return 0

        ids = [str(p.id) for p in posts]
        placeholders = ",".join(["?"] * len(ids))

        before_row = self._conn.execute(
            f"SELECT count(*) FROM {_TABLE} WHERE id IN ({placeholders})",
            ids,
        ).fetchone()
        count_before = int(str(before_row[0])) if before_row is not None else 0

        params = [_post_to_params(p) for p in posts]
        self._conn.executemany(
            f"""
            INSERT OR IGNORE INTO {_TABLE}
                ({_INSERT_COLUMNS})
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            params,
        )

        after_row = self._conn.execute(
            f"SELECT count(*) FROM {_TABLE} WHERE id IN ({placeholders})",
            ids,
        ).fetchone()
        count_after = int(str(after_row[0])) if after_row is not None else 0

        inserted = count_after - count_before
        logger.debug(
            "enriched_posts.batch_saved",
            attempted=len(posts),
            inserted=inserted,
        )
        return inserted

    def get_by_bronze_post_id(self, bronze_post_id: str) -> EnrichedPost | None:
        row = self._conn.execute(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM {_TABLE}
            WHERE bronze_post_id = ?
            """,
            [bronze_post_id],
        ).fetchone()
        if row is None:
            return None
        return _row_to_enriched_post(row)

    def get_by_search(self, search_request_id: str) -> list[EnrichedPost]:
        rows = self._conn.execute(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM {_TABLE}
            WHERE search_request_id = ?
            ORDER BY posted_at DESC
            """,
            [search_request_id],
        ).fetchall()
        return [_row_to_enriched_post(row) for row in rows]

    def count_by_search(self, search_request_id: str) -> int:
        result_row = self._conn.execute(
            f"SELECT count(*) FROM {_TABLE} WHERE search_request_id = ?",
            [search_request_id],
        ).fetchone()
        return int(str(result_row[0])) if result_row is not None else 0
