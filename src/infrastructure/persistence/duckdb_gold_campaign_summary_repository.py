from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from src.domain.entities.gold_campaign_summary import GoldCampaignSummary

if TYPE_CHECKING:
    import duckdb

logger = structlog.get_logger()

_TABLE = "gold.gold_campaign_summary"

_INSERT_COLUMNS = (
    "id, search_request_id, keyword, start_date, end_date, "
    "total_posts, positive_pct, negative_pct, neutral_pct, "
    "avg_confidence, total_engagement, "
    "total_likes, total_shares, total_replies, total_views, "
    "top_hashtags, top_topics, platforms, "
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
    if isinstance(raw, list):
        return [str(item) for item in raw]
    return []


def _row_to_gold_campaign_summary(row: tuple[object, ...]) -> GoldCampaignSummary:
    (
        raw_id,
        raw_sr_id,
        raw_keyword,
        raw_start_date,
        raw_end_date,
        raw_total_posts,
        raw_positive_pct,
        raw_negative_pct,
        raw_neutral_pct,
        raw_avg_confidence,
        raw_total_engagement,
        raw_total_likes,
        raw_total_shares,
        raw_total_replies,
        raw_total_views,
        raw_top_hashtags,
        raw_top_topics,
        raw_platforms,
        raw_ai_version,
        raw_created_at,
    ) = row

    return GoldCampaignSummary(
        id=_resolve_uuid(raw_id),
        search_request_id=_resolve_uuid(raw_sr_id),
        keyword=str(raw_keyword),
        start_date=_resolve_date(raw_start_date),
        end_date=_resolve_date(raw_end_date),
        total_posts=int(str(raw_total_posts)),
        positive_pct=float(str(raw_positive_pct)) if raw_positive_pct is not None else None,
        negative_pct=float(str(raw_negative_pct)) if raw_negative_pct is not None else None,
        neutral_pct=float(str(raw_neutral_pct)) if raw_neutral_pct is not None else None,
        avg_confidence=float(str(raw_avg_confidence)) if raw_avg_confidence is not None else None,
        total_engagement=int(str(raw_total_engagement)),
        total_likes=int(str(raw_total_likes)),
        total_shares=int(str(raw_total_shares)),
        total_replies=int(str(raw_total_replies)),
        total_views=int(str(raw_total_views)),
        top_hashtags=_resolve_str_list(raw_top_hashtags),
        top_topics=_resolve_str_list(raw_top_topics),
        platforms=_resolve_str_list(raw_platforms),
        ai_version=int(str(raw_ai_version)),
        created_at=_resolve_datetime(raw_created_at) if raw_created_at is not None else datetime.now(),
    )


def _summary_to_params(summary: GoldCampaignSummary) -> tuple[object, ...]:
    return (
        str(summary.id),
        str(summary.search_request_id),
        summary.keyword,
        summary.start_date,
        summary.end_date,
        summary.total_posts,
        summary.positive_pct,
        summary.negative_pct,
        summary.neutral_pct,
        summary.avg_confidence,
        summary.total_engagement,
        summary.total_likes,
        summary.total_shares,
        summary.total_replies,
        summary.total_views,
        summary.top_hashtags,
        summary.top_topics,
        summary.platforms,
        summary.ai_version,
        summary.created_at,
    )


class DuckDBGoldCampaignSummaryRepository:

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def save(self, summary: GoldCampaignSummary) -> GoldCampaignSummary:
        self._conn.execute(
            f"DELETE FROM {_TABLE} WHERE search_request_id = ?",  # noqa: S608
            [str(summary.search_request_id)],
        )
        self._conn.execute(
            f"""
            INSERT INTO {_TABLE}
                ({_INSERT_COLUMNS})
            VALUES ({",".join(["?"] * 20)})
            """,  # noqa: S608
            list(_summary_to_params(summary)),
        )
        logger.debug(
            "gold_campaign_summary.saved",
            summary_id=str(summary.id),
            search_request_id=str(summary.search_request_id),
        )
        return summary

    def get_by_search_request(self, search_request_id: str) -> GoldCampaignSummary | None:
        row = self._conn.execute(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM {_TABLE}
            WHERE search_request_id = ?
            """,  # noqa: S608
            [search_request_id],
        ).fetchone()
        if row is None:
            return None
        return _row_to_gold_campaign_summary(row)

    def get_all_summaries(self) -> list[GoldCampaignSummary]:
        rows = self._conn.execute(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM {_TABLE}
            ORDER BY created_at DESC
            """,  # noqa: S608
        ).fetchall()
        return [_row_to_gold_campaign_summary(row) for row in rows]
