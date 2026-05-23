from __future__ import annotations

import argparse
import asyncio
import sys
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

logger = structlog.get_logger()


async def _build_for_request(
    conn: duckdb.DuckDBPyConnection,
    search_request_id: str,
    keyword: str,
    start_date: date,
    end_date: date,
) -> None:
    enriched_repo = DuckDBEnrichedPostRepository(conn)
    ai_enrichment_repo = DuckDBAIEnrichmentRepository(conn)
    gold_post_search_repo = DuckDBGoldPostSearchRepository(conn)
    gold_daily_repo = DuckDBGoldCampaignDailyRepository(conn)
    gold_summary_repo = DuckDBGoldCampaignSummaryRepository(conn)

    crawl_row = conn.execute(
        "SELECT id FROM bronze.bronze_crawl_runs "
        "WHERE search_request_id = ? AND status = 'completed' "
        "ORDER BY completed_at DESC LIMIT 1",
        [search_request_id],
    ).fetchone()
    source_crawl_run_id = str(crawl_row[0]) if crawl_row else None

    job_row = conn.execute(
        "SELECT j.id FROM silver.ai_jobs j "
        "JOIN silver.silver_posts sp ON j.silver_post_id = sp.id "
        "WHERE sp.search_request_id = ? AND j.status = 'completed' "
        "ORDER BY j.completed_at DESC LIMIT 1",
        [search_request_id],
    ).fetchone()
    enrichment_job_id = str(job_row[0]) if job_row else None

    build_post_search = BuildPostSearch(enriched_repo, ai_enrichment_repo, gold_post_search_repo)
    build_daily = BuildCampaignDaily(gold_post_search_repo, gold_daily_repo)
    build_summary = BuildCampaignSummary(gold_post_search_repo, gold_summary_repo)

    await build_post_search.execute(
        search_request_id,
        keyword,
        source_crawl_run_id=source_crawl_run_id,
        enrichment_job_id=enrichment_job_id,
    )
    await build_daily.execute(
        search_request_id,
        source_crawl_run_id=source_crawl_run_id,
        enrichment_job_id=enrichment_job_id,
    )
    await build_summary.execute(
        search_request_id,
        start_date,
        end_date,
        source_crawl_run_id=source_crawl_run_id,
        enrichment_job_id=enrichment_job_id,
    )


def cli_main() -> None:
    parser = argparse.ArgumentParser(description="Build Gold layer tables for SocialPulse")
    parser.add_argument("--search-request-id", help="Specific search request to build")
    parser.add_argument("--keyword", help="Keyword (needed with --search-request-id)")

    args = parser.parse_args()

    try:
        import duckdb  # noqa: PLC0415

        conn = duckdb.connect(settings.db_path)
        try:
            create_all_tables(conn)

            if args.search_request_id:
                rows = conn.execute(
                    "SELECT keyword, start_date, end_date FROM bronze.search_requests WHERE id = ?",
                    [args.search_request_id],
                ).fetchall()

                if not rows:
                    logger.error(
                        "search_request_not_found", search_request_id=args.search_request_id
                    )
                    sys.exit(1)

                keyword, start_date, end_date = rows[0]
                keyword = args.keyword or str(keyword)

                sd = (
                    start_date
                    if isinstance(start_date, date)
                    else date.fromisoformat(str(start_date))
                )
                ed = end_date if isinstance(end_date, date) else date.fromisoformat(str(end_date))

                asyncio.run(_build_for_request(conn, args.search_request_id, keyword, sd, ed))
            else:
                rows = conn.execute(
                    "SELECT id, keyword, start_date, end_date "
                    "FROM bronze.search_requests "
                    "WHERE status = 'completed'"
                ).fetchall()

                if not rows:
                    logger.info("gold_build_no_completed_requests")
                    return

                for request_id, keyword, start_date, end_date in rows:
                    sd = (
                        start_date
                        if isinstance(start_date, date)
                        else date.fromisoformat(str(start_date))
                    )
                    ed = (
                        end_date
                        if isinstance(end_date, date)
                        else date.fromisoformat(str(end_date))
                    )

                    logger.info(
                        "gold_building", search_request_id=str(request_id), keyword=str(keyword)
                    )
                    try:
                        asyncio.run(_build_for_request(conn, str(request_id), str(keyword), sd, ed))
                    except Exception:
                        logger.exception("gold_build_failed", search_request_id=str(request_id))

            logger.info("gold_build_completed")

        finally:
            conn.close()

    except Exception as exc:
        logger.exception("gold_build_error", error=str(exc))
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
