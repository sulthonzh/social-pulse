"""Background AI enrichment worker for the SocialPulse Silver layer.

Polls bronze.bronze_posts for raw posts that have not yet been enriched,
then runs the EnrichPostUseCase to produce Silver-layer records.

Usage:
    python -m src.infrastructure.ai.worker
"""

from __future__ import annotations

import asyncio
import contextlib
import signal
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
from src.infrastructure.persistence.duckdb_ai_job_repository import (
    DuckDBAIJobRepository,
)
from src.infrastructure.persistence.duckdb_enriched_post_repository import (
    DuckDBEnrichedPostRepository,
)
from src.infrastructure.persistence.duckdb_post_repository import (
    DuckDBPostRepository,
)
from src.infrastructure.persistence.migrations import create_all_tables
from src.shared.config import settings

if TYPE_CHECKING:
    import duckdb

logger = structlog.get_logger()

_POLL_INTERVAL_SECONDS: int = 30
_BATCH_SIZE: int = 100

_UNENRICHED_SQL = """
    SELECT bp.id,
           bp.search_request_id,
           bp.crawl_run_id,
           bp.platform,
           bp.platform_id,
           bp.author_handle,
           bp.raw_payload,
           bp.fetched_at
    FROM bronze.bronze_posts bp
    LEFT JOIN silver.silver_posts sp ON sp.bronze_post_id = bp.id
    WHERE sp.id IS NULL
    ORDER BY bp.fetched_at
    LIMIT ?
"""


def _row_to_raw_post(row: tuple[object, ...]) -> RawPost:
    """Convert a DuckDB row to a RawPost entity."""
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


class AIEnrichmentWorker:
    """Polls for unenriched bronze posts and runs AI enrichment."""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn
        self._shutdown_event = asyncio.Event()

        DuckDBPostRepository(conn)
        enriched_post_repo = DuckDBEnrichedPostRepository(conn)
        ai_enrichment_repo = DuckDBAIEnrichmentRepository(conn)
        ai_job_repo = DuckDBAIJobRepository(conn)

        sentiment_analyzer = TransformerSentimentAnalyzer(
            model_name=settings.sentiment_model,
        )
        topic_extractor = KeyBERTTopicExtractor(
            model_name=settings.topic_model,
        )
        language_detector = LinguaLanguageDetector()

        self._use_case = EnrichPostUseCase(
            sentiment_analyzer=sentiment_analyzer,
            topic_extractor=topic_extractor,
            language_detector=language_detector,
            enriched_post_repo=enriched_post_repo,
            ai_enrichment_repo=ai_enrichment_repo,
            ai_job_repo=ai_job_repo,
        )

    def _fetch_unenriched_posts(self) -> list[RawPost]:
        """Find bronze posts that have no corresponding silver record."""
        rows = self._conn.execute(
            _UNENRICHED_SQL,
            [_BATCH_SIZE],
        ).fetchall()
        return [_row_to_raw_post(row) for row in rows]

    async def _process_post(self, raw_post: RawPost) -> None:
        """Run enrichment for a single post, catching errors."""
        post_id = str(raw_post.id)
        logger.info("job_processing", raw_post_id=post_id)
        try:
            await self._use_case.execute(raw_post)
            logger.info("job_completed", raw_post_id=post_id)
        except Exception:
            logger.exception("job_failed", raw_post_id=post_id)

    async def _run_once(self) -> int:
        """Single poll iteration. Returns number of posts processed."""
        posts = self._fetch_unenriched_posts()
        if not posts:
            return 0

        logger.info("batch_started", pending_count=len(posts))
        for raw_post in posts:
            if self._shutdown_event.is_set():
                break
            await self._process_post(raw_post)
        return len(posts)

    async def run_forever(self) -> None:
        """Main loop: poll, process, sleep, repeat until shutdown."""
        logger.info(
            "worker_started",
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
        logger.info("worker_stopped")

    def request_shutdown(self) -> None:
        """Signal the worker to stop after current work completes."""
        self._shutdown_event.set()


async def run(conn: duckdb.DuckDBPyConnection) -> None:
    """Entry point: run migrations, wire up the worker, handle signals."""
    create_all_tables(conn)

    worker = AIEnrichmentWorker(conn)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            worker.request_shutdown,
        )

    await worker.run_forever()


async def main() -> None:
    """Create a DuckDB connection and start the worker.

    Retries with exponential backoff when the database is locked
    by another process (e.g., the Streamlit app).
    """
    import time  # noqa: PLC0415

    import duckdb  # noqa: PLC0415

    max_retries = 5
    base_delay = 2.0

    for attempt in range(1, max_retries + 1):
        try:
            conn = duckdb.connect(settings.db_path)
            break
        except duckdb.IOException as exc:
            if "lock" not in str(exc).lower() or attempt == max_retries:
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "db_locked_retry",
                attempt=attempt,
                max_retries=max_retries,
                delay=delay,
            )
            time.sleep(delay)
    else:
        raise RuntimeError("Failed to acquire DuckDB lock after retries")

    try:
        await run(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
