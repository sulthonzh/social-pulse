from __future__ import annotations

import asyncio
from datetime import date
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    import duckdb

from src.application.use_cases.build_campaign_daily import BuildCampaignDaily
from src.application.use_cases.build_campaign_summary import BuildCampaignSummary
from src.application.use_cases.build_post_search import BuildPostSearch
from src.infrastructure.persistence.duckdb_ai_enrichment_repository import (
    DuckDBAIEnrichmentRepository,
)
from src.infrastructure.persistence.duckdb_enriched_post_repository import (
    DuckDBEnrichedPostRepository,
)
from src.infrastructure.persistence.duckdb_gold_build_tracking_repository import (
    DuckDBGoldBuildTrackingRepository,
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
from src.infrastructure.persistence.migrations import create_all_tables
from src.shared.config import settings

logger = structlog.get_logger(__name__)


class GoldBuilder:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

        self._enriched_post_repo = DuckDBEnrichedPostRepository(conn)
        self._ai_enrichment_repo = DuckDBAIEnrichmentRepository(conn)
        self._gold_post_search_repo = DuckDBGoldPostSearchRepository(conn)
        self._gold_daily_repo = DuckDBGoldCampaignDailyRepository(conn)
        self._gold_summary_repo = DuckDBGoldCampaignSummaryRepository(conn)
        self._tracking_repo = DuckDBGoldBuildTrackingRepository(conn)

        self._build_post_search = BuildPostSearch(
            self._enriched_post_repo,
            self._ai_enrichment_repo,
            self._gold_post_search_repo,
        )
        self._build_campaign_daily = BuildCampaignDaily(
            self._gold_post_search_repo,
            self._gold_daily_repo,
        )
        self._build_campaign_summary = BuildCampaignSummary(
            self._gold_post_search_repo,
            self._gold_summary_repo,
        )

    async def run(self) -> None:
        create_all_tables(self._conn)

        logger.info("builder_started")

        rows = self._conn.execute(
            "SELECT id, keyword, start_date, end_date "
            "FROM bronze.search_requests "
            "WHERE status = 'completed'"
        ).fetchall()

        if not rows:
            logger.info("builder_no_completed_requests")
            return

        batch_size = settings.gold_rebuild_batch_size
        total = min(len(rows), batch_size)

        logger.info(
            "builder_requests_found",
            total_completed=len(rows),
            batch_size=batch_size,
            processing=total,
        )

        for idx, (request_id, keyword, start_date, end_date) in enumerate(
            rows[:batch_size], start=1
        ):
            logger.info(
                "building_search",
                index=idx,
                total=total,
                search_request_id=str(request_id),
                keyword=keyword,
            )

            rid = str(request_id)
            last_build = self._tracking_repo.get_last_build(rid)

            if last_build is not None:
                logger.info(
                    "incremental_build",
                    search_request_id=rid,
                    last_build=last_build.isoformat(),
                )
                new_posts = self._enriched_post_repo.get_enriched_since(rid, last_build)

                if not new_posts:
                    logger.info(
                        "build_skipped_no_new_posts",
                        search_request_id=rid,
                    )
                    continue

                self._gold_post_search_repo.delete_by_search_request(rid)
                self._gold_daily_repo.delete_by_search_request(rid)

                posts_processed = await self._build_post_search.execute(
                    rid, keyword, since=last_build
                )
            else:
                logger.info(
                    "full_build",
                    search_request_id=rid,
                )

                posts_processed = await self._build_post_search.execute(rid, keyword)

            await self._build_campaign_daily.execute(rid)
            await self._build_campaign_summary.execute(
                rid,
                start_date if isinstance(start_date, date) else date.fromisoformat(str(start_date)),
                end_date if isinstance(end_date, date) else date.fromisoformat(str(end_date)),
            )

            self._tracking_repo.record_build(rid, posts_processed)

            logger.info(
                "build_completed",
                index=idx,
                total=total,
                search_request_id=rid,
            )

        logger.info("builder_finished", total_processed=total)


async def run() -> None:
    from src.shared.db_retry import connect_with_retry  # noqa: PLC0415

    conn: duckdb.DuckDBPyConnection = connect_with_retry()

    try:
        builder = GoldBuilder(conn)
        await builder.run()
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(run())
