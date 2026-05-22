from __future__ import annotations

import json
from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from src.application.use_cases.build_campaign_daily import BuildCampaignDaily
from src.application.use_cases.build_campaign_summary import BuildCampaignSummary
from src.application.use_cases.build_post_search import BuildPostSearch
from src.application.use_cases.enrich_post import EnrichPostUseCase
from src.application.use_cases.ingest_crawl import IngestCrawlRun
from src.application.use_cases.search_posts import SearchPosts
from src.domain.value_objects.platform import Platform
from src.infrastructure.crawling import create_crawler
from src.infrastructure.persistence.duckdb_ai_enrichment_repository import (
    DuckDBAIEnrichmentRepository,
)
from src.infrastructure.persistence.duckdb_ai_job_repository import (
    DuckDBAIJobRepository,
)
from src.infrastructure.persistence.duckdb_crawl_run_repository import (
    DuckDBCrawlRunRepository,
)
from src.infrastructure.persistence.duckdb_enriched_post_repository import (
    DuckDBEnrichedPostRepository,
)
from src.infrastructure.persistence.duckdb_gold_campaign_daily_repository import (
    DuckDBGoldCampaignDailyRepository,
)
from src.infrastructure.persistence.duckdb_gold_campaign_summary_repository import (
    DuckDBGoldCampaignSummaryRepository,
)
from src.infrastructure.persistence.duckdb_gold_post_search_repository import (
    DuckDBGoldPostSearchRepository,
)
from src.infrastructure.persistence.duckdb_post_repository import (
    DuckDBPostRepository,
)
from src.infrastructure.persistence.duckdb_search_request_repository import (
    DuckDBSearchRequestRepository,
)
from src.shared.config import settings

if TYPE_CHECKING:
    from collections.abc import Callable

    import duckdb

    from src.domain.entities.raw_post import RawPost
    from src.domain.interfaces import LanguageDetector, SentimentAnalyzer, TopicExtractor

logger = structlog.get_logger(__name__)


class PipelineResult:
    """Summary of a completed pipeline run."""

    __slots__ = ("gold_built", "posts_crawled", "posts_enriched", "search_request_id")

    def __init__(
        self,
        search_request_id: str,
        posts_crawled: int,
        posts_enriched: int,
        gold_built: bool,
    ) -> None:
        self.search_request_id = search_request_id
        self.posts_crawled = posts_crawled
        self.posts_enriched = posts_enriched
        self.gold_built = gold_built

    def __repr__(self) -> str:
        return (
            f"PipelineResult(search_request_id={self.search_request_id!r}, "
            f"posts_crawled={self.posts_crawled}, "
            f"posts_enriched={self.posts_enriched}, "
            f"gold_built={self.gold_built})"
        )


_UNENRICHED_FOR_REQUEST_SQL = """
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
      AND bp.search_request_id = ?
    ORDER BY bp.fetched_at
"""


def _row_to_raw_post(row: tuple[object, ...]) -> RawPost:
    """Convert a DuckDB row to a RawPost entity."""
    from src.domain.entities.raw_post import RawPost  # noqa: PLC0415

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


class IngestPipeline:
    """Orchestrates the full medallion pipeline: crawl -> bronze -> enrich (silver) -> gold.

    All operations share the same DuckDB connection to respect the single-writer lock.
    Progress is reported via an optional callback suitable for Streamlit status display.
    """

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> None:
        self._conn = conn
        self._progress = progress_callback

        # -- Bronze repositories --
        search_request_repo = DuckDBSearchRequestRepository(conn)
        crawl_run_repo = DuckDBCrawlRunRepository(conn)
        post_repo = DuckDBPostRepository(conn)

        # -- Silver repositories --
        enriched_post_repo = DuckDBEnrichedPostRepository(conn)
        ai_enrichment_repo = DuckDBAIEnrichmentRepository(conn)
        ai_job_repo = DuckDBAIJobRepository(conn)

        # -- Gold repositories --
        gold_post_search_repo = DuckDBGoldPostSearchRepository(conn)
        gold_daily_repo = DuckDBGoldCampaignDailyRepository(conn)
        gold_summary_repo = DuckDBGoldCampaignSummaryRepository(conn)

        # -- AI adapters (same initialization logic as worker.py) --
        sentiment_analyzer: SentimentAnalyzer
        topic_extractor: TopicExtractor
        language_detector: LanguageDetector
        if settings.ai_provider == "openai":
            from src.infrastructure.ai.openai_client import OpenAIClient  # noqa: PLC0415
            from src.infrastructure.ai.openai_language_detector import (  # noqa: PLC0415
                OpenAILanguageDetector,
            )
            from src.infrastructure.ai.openai_sentiment_analyzer import (  # noqa: PLC0415
                OpenAISentimentAnalyzer,
            )
            from src.infrastructure.ai.openai_topic_extractor import (  # noqa: PLC0415
                OpenAITopicExtractor,
            )

            openai_client = OpenAIClient(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                model=settings.openai_model,
            )
            sentiment_analyzer = OpenAISentimentAnalyzer(openai_client)
            topic_extractor = OpenAITopicExtractor(openai_client)
            language_detector = OpenAILanguageDetector(openai_client)
            logger.info("pipeline_using_openai", model=settings.openai_model)
        else:
            from src.infrastructure.ai.language_detector import (  # noqa: PLC0415
                LinguaLanguageDetector,
            )
            from src.infrastructure.ai.sentiment_analyzer import (  # noqa: PLC0415
                TransformerSentimentAnalyzer,
            )
            from src.infrastructure.ai.topic_extractor import (  # noqa: PLC0415
                KeyBERTTopicExtractor,
            )

            sentiment_analyzer = TransformerSentimentAnalyzer(
                model_name=settings.sentiment_model,
            )
            topic_extractor = KeyBERTTopicExtractor(
                model_name=settings.topic_model,
            )
            language_detector = LinguaLanguageDetector()
            logger.info("pipeline_using_local")

        # -- Use cases --
        self._search_posts = SearchPosts(search_request_repo)
        self._ingest_crawl = IngestCrawlRun(search_request_repo, crawl_run_repo, post_repo)
        self._enrich_post = EnrichPostUseCase(
            sentiment_analyzer=sentiment_analyzer,
            topic_extractor=topic_extractor,
            language_detector=language_detector,
            enriched_post_repo=enriched_post_repo,
            ai_enrichment_repo=ai_enrichment_repo,
            ai_job_repo=ai_job_repo,
        )
        self._build_post_search = BuildPostSearch(
            enriched_post_repo,
            ai_enrichment_repo,
            gold_post_search_repo,
        )
        self._build_campaign_daily = BuildCampaignDaily(
            gold_post_search_repo,
            gold_daily_repo,
        )
        self._build_campaign_summary = BuildCampaignSummary(
            gold_post_search_repo,
            gold_summary_repo,
        )

    def _report(self, stage: str, current: int, total: int) -> None:
        if self._progress is not None:
            self._progress(stage, current, total)

    async def execute(
        self,
        keyword: str,
        platform: Platform,
        start_date: date,
        end_date: date,
    ) -> PipelineResult:
        """Run the full pipeline: crawl -> enrich -> gold."""
        # -- Stage 1: Crawl (Bronze) --
        self._report("crawling", 0, 0)

        search_request = await self._search_posts.execute(keyword, platform, start_date, end_date)
        crawler = create_crawler(platform=platform)
        crawl_run = await self._ingest_crawl.execute(search_request, crawler)

        posts_crawled = crawl_run.posts_fetched
        search_request_id = str(search_request.id)
        self._report("crawling", 1, 1)

        logger.info(
            "pipeline_crawl_done",
            search_request_id=search_request_id,
            posts_crawled=posts_crawled,
        )

        if posts_crawled == 0:
            logger.info("pipeline_no_posts_early_return", search_request_id=search_request_id)
            return PipelineResult(
                search_request_id=search_request_id,
                posts_crawled=0,
                posts_enriched=0,
                gold_built=False,
            )

        # -- Stage 2: Enrich (Silver) --
        raw_posts = self._fetch_unenriched_posts(search_request_id)
        total = len(raw_posts)
        enriched_count = 0

        logger.info("pipeline_enriching_start", total_posts=total)

        for i, raw_post in enumerate(raw_posts, start=1):
            self._report("enriching", i, total)
            try:
                await self._enrich_post.execute(raw_post)
                enriched_count += 1
            except Exception:
                logger.exception(
                    "pipeline_enrich_post_failed",
                    raw_post_id=str(raw_post.id),
                    index=i,
                    total=total,
                )

        logger.info(
            "pipeline_enriching_done",
            search_request_id=search_request_id,
            enriched=enriched_count,
            failed=total - enriched_count,
        )

        # -- Stage 3: Build Gold --
        await self._build_post_search.execute(search_request_id, keyword)
        await self._build_campaign_daily.execute(search_request_id)
        await self._build_campaign_summary.execute(search_request_id, start_date, end_date)

        self._report("gold", 1, 1)

        logger.info(
            "pipeline_gold_done",
            search_request_id=search_request_id,
        )

        return PipelineResult(
            search_request_id=search_request_id,
            posts_crawled=posts_crawled,
            posts_enriched=enriched_count,
            gold_built=True,
        )

    def _fetch_unenriched_posts(self, search_request_id: str) -> list[RawPost]:
        """Find bronze posts for a given search request that have no silver record yet."""
        rows = self._conn.execute(
            _UNENRICHED_FOR_REQUEST_SQL,
            [search_request_id],
        ).fetchall()
        return [_row_to_raw_post(row) for row in rows]
