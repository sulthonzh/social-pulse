from __future__ import annotations

import asyncio
from datetime import date
from typing import TYPE_CHECKING

import structlog

from src.application.use_cases.build_campaign_daily import BuildCampaignDaily
from src.application.use_cases.build_campaign_summary import BuildCampaignSummary
from src.application.use_cases.build_post_search import BuildPostSearch
from src.infrastructure.persistence.duckdb_ai_enrichment_repository import (
    DuckDBAIEnrichmentRepository,
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
from src.infrastructure.persistence.migrations import create_all_tables
from src.shared.config import settings

if TYPE_CHECKING:
    import duckdb

logger = structlog.get_logger(__name__)


class GoldBuilder:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

        self._enriched_post_repo = DuckDBEnrichedPostRepository(conn)
        self._ai_enrichment_repo = DuckDBAIEnrichmentRepository(conn)
        self._gold_post_search_repo = DuckDBGoldPostSearchRepository(conn)
        self._gold_daily_repo = DuckDBGoldCampaignDailyRepository(conn)
        self._gold_summary_repo = DuckDBGoldCampaignSummaryRepository(conn)

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

            await self._build_post_search.execute(str(request_id), keyword)
            await self._build_campaign_daily.execute(str(request_id))
            await self._build_campaign_summary.execute(
                str(request_id),
                start_date if isinstance(start_date, date) else date.fromisoformat(str(start_date)),
                end_date if isinstance(end_date, date) else date.fromisoformat(str(end_date)),
            )

            logger.info(
                "build_completed",
                index=idx,
                total=total,
                search_request_id=str(request_id),
            )

        logger.info("builder_finished", total_processed=total)


async def run() -> None:
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
        builder = GoldBuilder(conn)
        await builder.run()
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(run())
