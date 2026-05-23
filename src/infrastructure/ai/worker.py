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

if TYPE_CHECKING:
    import duckdb

from src.application.use_cases.enrich_post import EnrichPostUseCase
from src.domain.entities.raw_post import RawPost
from src.domain.exceptions import EnrichmentError
from src.domain.value_objects.platform import Platform
from src.infrastructure.ai.language_detector import LinguaLanguageDetector
from src.infrastructure.ai.openai_client import OpenAIClient
from src.infrastructure.ai.openai_language_detector import OpenAILanguageDetector
from src.infrastructure.ai.openai_sentiment_analyzer import OpenAISentimentAnalyzer
from src.infrastructure.ai.openai_topic_extractor import OpenAITopicExtractor
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
from src.shared.circuit_breaker import CircuitBreaker, CircuitOpenError
from src.shared.config import settings
from src.shared.worker_health import WorkerHealthServer

if TYPE_CHECKING:
    from src.domain.interfaces import (
        LanguageDetector,
        SentimentAnalyzer,
        TopicExtractor,
    )

logger = structlog.get_logger()

_POLL_INTERVAL_SECONDS: int = 30
_BATCH_SIZE: int = 100


def _resolve_provider(feature_override: str) -> str:
    return feature_override if feature_override else settings.ai_provider


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
    import json
    from datetime import datetime
    from uuid import UUID

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

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        health_server: WorkerHealthServer | None = None,
    ) -> None:
        self._conn = conn
        self._health_server = health_server
        self._shutdown_event = asyncio.Event()
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=settings.circuit_breaker_failure_threshold,
            cooldown_seconds=settings.circuit_breaker_cooldown_seconds,
            name="ai_enrichment",
        )

        DuckDBPostRepository(conn)
        enriched_post_repo = DuckDBEnrichedPostRepository(conn)
        ai_enrichment_repo = DuckDBAIEnrichmentRepository(conn)
        ai_job_repo = DuckDBAIJobRepository(conn)

        sentiment_provider = _resolve_provider(settings.sentiment_provider)
        topic_provider = _resolve_provider(settings.topic_provider)
        language_provider = _resolve_provider(settings.language_provider)

        self._sentiment_analyzer = self._create_sentiment_analyzer(sentiment_provider)
        self._topic_extractor = self._create_topic_extractor(topic_provider)
        self._language_detector = self._create_language_detector(language_provider)

        self._use_case = EnrichPostUseCase(
            sentiment_analyzer=self._sentiment_analyzer,
            topic_extractor=self._topic_extractor,
            language_detector=self._language_detector,
            enriched_post_repo=enriched_post_repo,
            ai_enrichment_repo=ai_enrichment_repo,
            ai_job_repo=ai_job_repo,
        )

    @staticmethod
    def _get_openai_client() -> OpenAIClient:
        return OpenAIClient(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
        )

    def _create_sentiment_analyzer(self, provider: str) -> SentimentAnalyzer:
        if provider == "openai":
            return OpenAISentimentAnalyzer(self._get_openai_client())
        return TransformerSentimentAnalyzer(model_name=settings.sentiment_model)

    def _create_topic_extractor(self, provider: str) -> TopicExtractor:
        if provider == "openai":
            return OpenAITopicExtractor(self._get_openai_client())
        return KeyBERTTopicExtractor(model_name=settings.topic_model)

    def _create_language_detector(self, provider: str) -> LanguageDetector:
        if provider == "openai":
            return OpenAILanguageDetector(self._get_openai_client())
        return LinguaLanguageDetector()

    def _fetch_unenriched_posts(self) -> list[RawPost]:
        """Find bronze posts that have no corresponding silver record."""
        rows = self._conn.execute(
            _UNENRICHED_SQL,
            [_BATCH_SIZE],
        ).fetchall()
        return [_row_to_raw_post(row) for row in rows]

    async def _process_post(self, raw_post: RawPost) -> None:
        post_id = str(raw_post.id)
        logger.info("job_processing", raw_post_id=post_id)
        try:
            await self._circuit_breaker.call(self._use_case.execute, raw_post)
            logger.info("job_completed", raw_post_id=post_id)
            if self._health_server is not None:
                self._health_server.record_job_processed()
        except CircuitOpenError:
            logger.warning("job_skipped_circuit_open", raw_post_id=post_id)
        except EnrichmentError:
            logger.exception("job_failed", raw_post_id=post_id)
            if self._health_server is not None:
                self._health_server.record_error()

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

    def _cleanup(self) -> None:
        for adapter in (self._topic_extractor, self._language_detector):
            if hasattr(adapter, "cleanup"):
                adapter.cleanup()

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
        self._cleanup()

    def request_shutdown(self) -> None:
        """Signal the worker to stop after current work completes."""
        self._shutdown_event.set()


async def run(conn: duckdb.DuckDBPyConnection) -> None:
    """Entry point: run migrations, wire up the worker, handle signals."""
    create_all_tables(conn)

    health_server = WorkerHealthServer(port=settings.worker_health_port)
    health_server.start()
    logger.info("health_server_started", port=settings.worker_health_port)

    worker = AIEnrichmentWorker(conn, health_server=health_server)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            worker.request_shutdown,
        )

    try:
        await worker.run_forever()
    finally:
        health_server.stop()


async def main() -> None:
    """Create a DuckDB connection and start the worker.

    Retries with exponential backoff when the database is locked
    by another process (e.g., the Streamlit app).
    """
    from src.shared.db_retry import connect_with_retry

    conn: duckdb.DuckDBPyConnection = connect_with_retry()

    try:
        await run(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
