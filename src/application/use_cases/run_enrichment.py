from __future__ import annotations

import argparse
import asyncio
import sys
from typing import TYPE_CHECKING

import structlog

from src.application.use_cases.enrich_post import EnrichPostUseCase
from src.domain.entities.raw_post import RawPost
from src.domain.value_objects.platform import Platform
from src.infrastructure.ai.language_detector import LinguaLanguageDetector
from src.infrastructure.ai.sentiment_analyzer import TransformerSentimentAnalyzer
from src.infrastructure.ai.topic_extractor import KeyBERTTopicExtractor
from src.infrastructure.persistence.duckdb_ai_enrichment_repository import (
    DuckDBAIEnrichmentRepository,
)
from src.infrastructure.persistence.duckdb_ai_job_repository import DuckDBAIJobRepository
from src.infrastructure.persistence.duckdb_enriched_post_repository import (
    DuckDBEnrichedPostRepository,
)
from src.infrastructure.persistence.migrations import create_all_tables
from src.shared.config import settings

if TYPE_CHECKING:
    import duckdb

logger = structlog.get_logger()

_UNENRICHED_SQL = """
    SELECT bp.id, bp.search_request_id, bp.crawl_run_id, bp.platform,
           bp.platform_id, bp.author_handle, bp.raw_payload, bp.fetched_at
    FROM bronze.bronze_posts bp
    LEFT JOIN silver.silver_posts sp ON sp.bronze_post_id = bp.id
    WHERE sp.id IS NULL
    ORDER BY bp.fetched_at
    LIMIT ?
"""


def _row_to_raw_post(row: tuple[object, ...]) -> RawPost:
    import json  # noqa: PLC0415
    from datetime import datetime  # noqa: PLC0415
    from uuid import UUID  # noqa: PLC0415

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


async def _run_enrichment(conn: duckdb.DuckDBPyConnection, limit: int) -> None:
    enriched_repo = DuckDBEnrichedPostRepository(conn)
    ai_enrichment_repo = DuckDBAIEnrichmentRepository(conn)
    ai_job_repo = DuckDBAIJobRepository(conn)

    sentiment_analyzer = TransformerSentimentAnalyzer(model_name=settings.sentiment_model)
    topic_extractor = KeyBERTTopicExtractor(model_name=settings.topic_model)
    language_detector = LinguaLanguageDetector()

    use_case = EnrichPostUseCase(
        sentiment_analyzer=sentiment_analyzer,
        topic_extractor=topic_extractor,
        language_detector=language_detector,
        enriched_post_repo=enriched_repo,
        ai_enrichment_repo=ai_enrichment_repo,
        ai_job_repo=ai_job_repo,
    )

    rows = conn.execute(_UNENRICHED_SQL, [limit]).fetchall()
    posts = [_row_to_raw_post(row) for row in rows]

    if not posts:
        logger.info("enrichment_no_pending")
        return

    logger.info("enrichment_started", pending_count=len(posts))

    processed = 0
    for post in posts:
        try:
            await use_case.execute(post)
            processed += 1
        except Exception:
            logger.exception("enrichment_post_failed", raw_post_id=str(post.id))

    logger.info("enrichment_completed", processed=processed, total=len(posts))


def cli_main() -> None:
    parser = argparse.ArgumentParser(description="Trigger AI enrichment for SocialPulse posts")
    parser.add_argument("--search-request-id", help="Specific search request to enrich")
    parser.add_argument("--limit", type=int, default=100)

    args = parser.parse_args()

    try:
        import duckdb  # noqa: PLC0415

        conn = duckdb.connect(settings.db_path)
        try:
            create_all_tables(conn)
            asyncio.run(_run_enrichment(conn, args.limit))
        finally:
            conn.close()

    except Exception as exc:
        logger.exception("enrichment_failed", error=str(exc))
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
