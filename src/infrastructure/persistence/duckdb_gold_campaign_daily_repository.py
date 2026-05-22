from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import TYPE_CHECKING, cast
from uuid import UUID

import structlog

from src.domain.entities.gold_campaign_daily import GoldCampaignDaily
from src.domain.value_objects.platform import Platform

if TYPE_CHECKING:
    import duckdb

logger = structlog.get_logger()

_TABLE = "gold.gold_campaign_daily"

_INSERT_COLUMNS = (
    "id, search_request_id, keyword, platform, date, "
    "total_posts, positive_count, negative_count, neutral_count, "
    "avg_confidence, top_hashtags, top_topics, "
    "total_likes, total_shares, total_replies, total_views, "
    "ai_version, created_at"
)

_SELECT_COLUMNS = _INSERT_COLUMNS


def _resolve_uuid(raw: object) -> UUID:
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def _resolve_date(raw: object) -> date:
    if isinstance(raw, date):
        return raw
    return date.fromisoformat(str(raw))


def _resolve_datetime(raw: object) -> datetime | None:
    if raw is None:
        return None
    return raw if isinstance(raw, datetime) else datetime.fromisoformat(str(raw))


def _resolve_str_list(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, Sequence) and not isinstance(raw, str):
        items = cast("Sequence[object]", raw)
        return [str(item) for item in items]
    return []


def _row_to_gold_campaign_daily(row: tuple[object, ...]) -> GoldCampaignDaily:
    (
        raw_id,
        raw_sr_id,
        raw_keyword,
        raw_platform,
        raw_date,
        raw_total_posts,
        raw_positive_count,
        raw_negative_count,
        raw_neutral_count,
        raw_avg_confidence,
        raw_top_hashtags,
        raw_top_topics,
        raw_total_likes,
        raw_total_shares,
        raw_total_replies,
        raw_total_views,
        raw_ai_version,
        raw_created_at,
    ) = row

    return GoldCampaignDaily(
        id=_resolve_uuid(raw_id),
        search_request_id=_resolve_uuid(raw_sr_id),
        keyword=str(raw_keyword),
        platform=Platform(str(raw_platform)),
        date=_resolve_date(raw_date),
        total_posts=int(str(raw_total_posts)),
        positive_count=int(str(raw_positive_count)),
        negative_count=int(str(raw_negative_count)),
        neutral_count=int(str(raw_neutral_count)),
        avg_confidence=float(str(raw_avg_confidence)) if raw_avg_confidence is not None else None,
        top_hashtags=_resolve_str_list(raw_top_hashtags),
        top_topics=_resolve_str_list(raw_top_topics),
        total_likes=int(str(raw_total_likes)),
        total_shares=int(str(raw_total_shares)),
        total_replies=int(str(raw_total_replies)),
        total_views=int(str(raw_total_views)),
        ai_version=int(str(raw_ai_version)),
        created_at=_resolve_datetime(raw_created_at) or datetime.now(),
    )


def _record_to_params(record: GoldCampaignDaily) -> tuple[object, ...]:
    return (
        str(record.id),
        str(record.search_request_id),
        record.keyword,
        record.platform.value,
        record.date,
        record.total_posts,
        record.positive_count,
        record.negative_count,
        record.neutral_count,
        record.avg_confidence,
        record.top_hashtags,
        record.top_topics,
        record.total_likes,
        record.total_shares,
        record.total_replies,
        record.total_views,
        record.ai_version,
        record.created_at,
    )


class DuckDBGoldCampaignDailyRepository:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def save_batch(self, records: list[GoldCampaignDaily]) -> int:
        if not records:
            return 0

        ids = [str(r.id) for r in records]
        placeholders = ",".join(["?"] * len(ids))

        before_row = self._conn.execute(
            f"SELECT count(*) FROM {_TABLE} WHERE id IN ({placeholders})",
            ids,
        ).fetchone()
        count_before = int(str(before_row[0])) if before_row is not None else 0

        params = [_record_to_params(r) for r in records]
        self._conn.executemany(
            f"""
            INSERT OR IGNORE INTO {_TABLE}
                ({_INSERT_COLUMNS})
            VALUES ({",".join(["?"] * 18)})
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
            "gold_campaign_daily.batch_saved",
            attempted=len(records),
            inserted=inserted,
        )
        return inserted

    def get_by_search_request(self, search_request_id: str) -> list[GoldCampaignDaily]:
        rows = self._conn.execute(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM {_TABLE}
            WHERE search_request_id = ?
            ORDER BY date ASC
            """,
            [search_request_id],
        ).fetchall()
        return [_row_to_gold_campaign_daily(row) for row in rows]

    def get_volume_trend(self, keyword: str) -> list[dict[str, object]]:
        rows = self._conn.execute(
            f"""
            SELECT date, total_posts
            FROM {_TABLE}
            WHERE keyword = ?
            ORDER BY date ASC
            """,
            [keyword],
        ).fetchall()
        return [{"date": str(row[0]), "total_posts": int(str(row[1]))} for row in rows]
