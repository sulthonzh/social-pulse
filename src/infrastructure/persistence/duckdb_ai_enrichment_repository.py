from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from src.domain.entities.ai_enrichment import AIEnrichment
from src.domain.value_objects.sentiment_label import SentimentLabel

if TYPE_CHECKING:
    import duckdb

logger = structlog.get_logger()

_TABLE = "silver.silver_ai_enrichment"

_INSERT_COLUMNS = (
    "id, silver_post_id, ai_version, hashtags, mentions, "
    "language, topic_label, topic_confidence, reach_estimate, "
    "sentiment, sentiment_confidence, "
    "metadata_model_name, metadata_model_version, "
    "sentiment_model_name, sentiment_model_version, "
    "created_at"
)

_SELECT_COLUMNS = _INSERT_COLUMNS


def _resolve_uuid(raw: object) -> UUID:
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def _resolve_datetime(raw: object) -> datetime:
    if raw is None:
        return datetime.now()
    return raw if isinstance(raw, datetime) else datetime.fromisoformat(str(raw))


def _resolve_str(raw: object) -> str | None:
    return str(raw) if raw is not None else None


def _resolve_str_list(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw]
    return []


def _row_to_ai_enrichment(row: tuple[object, ...]) -> AIEnrichment:
    (
        raw_id,
        raw_silver_post_id,
        raw_ai_version,
        raw_hashtags,
        raw_mentions,
        raw_language,
        raw_topic_label,
        raw_topic_confidence,
        raw_reach_estimate,
        raw_sentiment,
        raw_sentiment_confidence,
        raw_metadata_model_name,
        raw_metadata_model_version,
        raw_sentiment_model_name,
        raw_sentiment_model_version,
        raw_created_at,
    ) = row

    sentiment: SentimentLabel | None = None
    if raw_sentiment is not None:
        sentiment = SentimentLabel(str(raw_sentiment))

    return AIEnrichment(
        id=_resolve_uuid(raw_id),
        silver_post_id=_resolve_uuid(raw_silver_post_id),
        ai_version=int(str(raw_ai_version)),
        hashtags=_resolve_str_list(raw_hashtags),
        mentions=_resolve_str_list(raw_mentions),
        language=_resolve_str(raw_language),
        topic_label=_resolve_str(raw_topic_label),
        topic_confidence=float(str(raw_topic_confidence))
        if raw_topic_confidence is not None
        else None,
        reach_estimate=int(str(raw_reach_estimate)) if raw_reach_estimate is not None else None,
        sentiment=sentiment,
        sentiment_confidence=float(str(raw_sentiment_confidence))
        if raw_sentiment_confidence is not None
        else None,
        metadata_model_name=_resolve_str(raw_metadata_model_name),
        metadata_model_version=_resolve_str(raw_metadata_model_version),
        sentiment_model_name=_resolve_str(raw_sentiment_model_name),
        sentiment_model_version=_resolve_str(raw_sentiment_model_version),
        created_at=_resolve_datetime(raw_created_at),
    )


def _enrichment_to_params(enrichment: AIEnrichment) -> tuple[object, ...]:
    return (
        str(enrichment.id),
        str(enrichment.silver_post_id),
        enrichment.ai_version,
        enrichment.hashtags,
        enrichment.mentions,
        enrichment.language,
        enrichment.topic_label,
        enrichment.topic_confidence,
        enrichment.reach_estimate,
        enrichment.sentiment.value if enrichment.sentiment is not None else None,
        enrichment.sentiment_confidence,
        enrichment.metadata_model_name,
        enrichment.metadata_model_version,
        enrichment.sentiment_model_name,
        enrichment.sentiment_model_version,
        enrichment.created_at,
    )


class DuckDBAIEnrichmentRepository:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def save(self, enrichment: AIEnrichment) -> AIEnrichment:
        self._conn.execute(
            f"""
            INSERT OR IGNORE INTO {_TABLE}
                ({_INSERT_COLUMNS})
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            list(_enrichment_to_params(enrichment)),
        )
        logger.debug(
            "ai_enrichment.saved",
            enrichment_id=str(enrichment.id),
            silver_post_id=str(enrichment.silver_post_id),
            ai_version=enrichment.ai_version,
        )
        return enrichment

    def get_by_post(self, silver_post_id: str, ai_version: int = 1) -> AIEnrichment | None:
        row = self._conn.execute(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM {_TABLE}
            WHERE silver_post_id = ? AND ai_version = ?
            """,
            [silver_post_id, ai_version],
        ).fetchone()
        if row is None:
            return None
        return _row_to_ai_enrichment(row)

    def get_by_search(self, search_request_id: str, ai_version: int = 1) -> list[AIEnrichment]:
        rows = self._conn.execute(
            f"""
            SELECT e.{_SELECT_COLUMNS.replace(", ", ", e.")}
            FROM {_TABLE} e
            JOIN silver.silver_posts sp ON e.silver_post_id = sp.id
            WHERE sp.search_request_id = ? AND e.ai_version = ?
            ORDER BY e.created_at DESC
            """,
            [search_request_id, ai_version],
        ).fetchall()
        return [_row_to_ai_enrichment(row) for row in rows]

    def get_max_version(self, silver_post_id: str) -> int:
        row = self._conn.execute(
            f"SELECT MAX(ai_version) FROM {_TABLE} WHERE silver_post_id = ?",
            [silver_post_id],
        ).fetchone()
        if row is None or row[0] is None:
            return 0
        return int(str(row[0]))

    def get_by_posts(
        self, silver_post_ids: list[str], ai_version: int = 1
    ) -> dict[str, AIEnrichment]:
        if not silver_post_ids:
            return {}
        placeholders = ", ".join("?" for _ in silver_post_ids)
        rows = self._conn.execute(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM {_TABLE}
            WHERE silver_post_id IN ({placeholders}) AND ai_version = ?
            """,
            [*silver_post_ids, ai_version],
        ).fetchall()
        return {str(_resolve_uuid(row[1])): _row_to_ai_enrichment(row) for row in rows}
