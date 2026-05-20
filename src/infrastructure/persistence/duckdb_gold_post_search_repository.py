from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from src.domain.entities.gold_post_search import GoldPostSearch
from src.domain.value_objects.platform import Platform

if TYPE_CHECKING:
    import duckdb

logger = structlog.get_logger()

_TABLE = "gold.gold_post_search"

_INSERT_COLUMNS = (
    "id, search_request_id, keyword, platform, "
    "author_handle, author_name, post_text, posted_at, post_url, "
    "sentiment, sentiment_confidence, topic_label, language, "
    "hashtags, mentions, "
    "like_count, share_count, reply_count, view_count, "
    "ai_version, created_at"
)

_SELECT_COLUMNS = _INSERT_COLUMNS


def _resolve_uuid(raw: object) -> UUID:
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def _resolve_datetime(raw: object) -> datetime | None:
    if raw is None:
        return None
    return raw if isinstance(raw, datetime) else datetime.fromisoformat(str(raw))


def _resolve_str(raw: object) -> str | None:
    return str(raw) if raw is not None else None


def _resolve_str_list(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw]
    return []


def _row_to_gold_post_search(row: tuple[object, ...]) -> GoldPostSearch:
    (
        raw_id,
        raw_sr_id,
        raw_keyword,
        raw_platform,
        raw_author_handle,
        raw_author_name,
        raw_post_text,
        raw_posted_at,
        raw_post_url,
        raw_sentiment,
        raw_sentiment_confidence,
        raw_topic_label,
        raw_language,
        raw_hashtags,
        raw_mentions,
        raw_like_count,
        raw_share_count,
        raw_reply_count,
        raw_view_count,
        raw_ai_version,
        raw_created_at,
    ) = row

    return GoldPostSearch(
        id=_resolve_uuid(raw_id),
        search_request_id=_resolve_uuid(raw_sr_id),
        keyword=str(raw_keyword),
        platform=Platform(str(raw_platform)),
        author_handle=_resolve_str(raw_author_handle),
        author_name=_resolve_str(raw_author_name),
        post_text=_resolve_str(raw_post_text),
        posted_at=_resolve_datetime(raw_posted_at),
        post_url=_resolve_str(raw_post_url),
        sentiment=_resolve_str(raw_sentiment),
        sentiment_confidence=float(str(raw_sentiment_confidence)) if raw_sentiment_confidence is not None else None,
        topic_label=_resolve_str(raw_topic_label),
        language=_resolve_str(raw_language),
        hashtags=_resolve_str_list(raw_hashtags),
        mentions=_resolve_str_list(raw_mentions),
        like_count=int(str(raw_like_count)),
        share_count=int(str(raw_share_count)),
        reply_count=int(str(raw_reply_count)),
        view_count=int(str(raw_view_count)),
        ai_version=int(str(raw_ai_version)),
        created_at=_resolve_datetime(raw_created_at) if raw_created_at is not None else datetime.now(),
    )


def _post_to_params(post: GoldPostSearch) -> tuple[object, ...]:
    return (
        str(post.id),
        str(post.search_request_id),
        post.keyword,
        post.platform.value,
        post.author_handle,
        post.author_name,
        post.post_text,
        post.posted_at,
        post.post_url,
        post.sentiment,
        post.sentiment_confidence,
        post.topic_label,
        post.language,
        post.hashtags,
        post.mentions,
        post.like_count,
        post.share_count,
        post.reply_count,
        post.view_count,
        post.ai_version,
        post.created_at,
    )


class DuckDBGoldPostSearchRepository:

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def save_batch(self, posts: list[GoldPostSearch]) -> int:
        if not posts:
            return 0

        ids = [str(p.id) for p in posts]
        placeholders = ",".join(["?"] * len(ids))

        before_row = self._conn.execute(
            f"SELECT count(*) FROM {_TABLE} WHERE id IN ({placeholders})",  # noqa: S608
            ids,
        ).fetchone()
        count_before = int(str(before_row[0])) if before_row is not None else 0

        params = [_post_to_params(p) for p in posts]
        self._conn.executemany(
            f"""
            INSERT OR IGNORE INTO {_TABLE}
                ({_INSERT_COLUMNS})
            VALUES ({",".join(["?"] * 21)})
            """,  # noqa: S608
            params,
        )

        after_row = self._conn.execute(
            f"SELECT count(*) FROM {_TABLE} WHERE id IN ({placeholders})",  # noqa: S608
            ids,
        ).fetchone()
        count_after = int(str(after_row[0])) if after_row is not None else 0

        inserted = count_after - count_before
        logger.debug(
            "gold_post_search.batch_saved",
            attempted=len(posts),
            inserted=inserted,
        )
        return inserted

    def get_by_keyword(self, keyword: str, limit: int = 100, offset: int = 0) -> list[GoldPostSearch]:
        rows = self._conn.execute(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM {_TABLE}
            WHERE keyword = ?
            ORDER BY posted_at DESC
            LIMIT ? OFFSET ?
            """,  # noqa: S608
            [keyword, limit, offset],
        ).fetchall()
        return [_row_to_gold_post_search(row) for row in rows]

    def count_by_keyword(self, keyword: str) -> int:
        result_row = self._conn.execute(
            f"SELECT count(*) FROM {_TABLE} WHERE keyword = ?",  # noqa: S608
            [keyword],
        ).fetchone()
        return int(str(result_row[0])) if result_row is not None else 0

    def get_sentiment_breakdown(self, keyword: str) -> list[dict]:
        rows = self._conn.execute(
            f"""
            SELECT sentiment, count(*) as cnt
            FROM {_TABLE}
            WHERE keyword = ?
            GROUP BY sentiment
            ORDER BY cnt DESC
            """,  # noqa: S608
            [keyword],
        ).fetchall()
        return [
            {"sentiment": str(row[0]) if row[0] is not None else "unknown", "count": int(str(row[1]))}
            for row in rows
        ]

    def get_filtered(
        self,
        keyword: str,
        sentiment: str | None = None,
        platform: str | None = None,
        language: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GoldPostSearch]:
        conditions = ["keyword = ?"]
        params: list[object] = [keyword]

        if sentiment is not None:
            conditions.append("sentiment = ?")
            params.append(sentiment)
        if platform is not None:
            conditions.append("platform = ?")
            params.append(platform)
        if language is not None:
            conditions.append("language = ?")
            params.append(language)
        if date_from is not None:
            conditions.append("posted_at >= ?")
            params.append(date_from)
        if date_to is not None:
            conditions.append("posted_at < ?")
            params.append(date_to)

        where = " AND ".join(conditions)
        params.extend([limit, offset])

        rows = self._conn.execute(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM {_TABLE}
            WHERE {where}
            ORDER BY posted_at DESC
            LIMIT ? OFFSET ?
            """,  # noqa: S608
            params,
        ).fetchall()
        return [_row_to_gold_post_search(row) for row in rows]

    def get_by_search_request(self, search_request_id: str) -> list[GoldPostSearch]:
        rows = self._conn.execute(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM {_TABLE}
            WHERE search_request_id = ?
            ORDER BY posted_at DESC
            """,  # noqa: S608
            [search_request_id],
        ).fetchall()
        return [_row_to_gold_post_search(row) for row in rows]
