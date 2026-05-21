from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date

import structlog

from src.application.use_cases.ingest_crawl import IngestCrawlRun
from src.domain.entities.search_request import SearchRequest
from src.domain.value_objects.platform import Platform
from src.infrastructure.crawling import create_crawler
from src.infrastructure.persistence.duckdb_crawl_run_repository import DuckDBCrawlRunRepository
from src.infrastructure.persistence.duckdb_post_repository import DuckDBPostRepository
from src.infrastructure.persistence.duckdb_search_request_repository import (
    DuckDBSearchRequestRepository,
)
from src.infrastructure.persistence.migrations import create_all_tables
from src.shared.config import settings

logger = structlog.get_logger()


def main() -> None:
    parser = argparse.ArgumentParser(description="Trigger a crawl for SocialPulse")
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--platform", default="twitter", choices=["twitter"])
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")

    args = parser.parse_args()

    try:
        import duckdb  # noqa: PLC0415

        conn = duckdb.connect(settings.db_path)
        try:
            create_all_tables(conn)

            search_repo = DuckDBSearchRequestRepository(conn)
            crawl_repo = DuckDBCrawlRunRepository(conn)
            post_repo = DuckDBPostRepository(conn)
            crawler = create_crawler()

            use_case = IngestCrawlRun(search_repo, crawl_repo, post_repo)

            start = date.fromisoformat(args.start_date) if args.start_date else date.today()
            end = date.fromisoformat(args.end_date) if args.end_date else date.today()

            request = SearchRequest(
                keyword=args.keyword,
                start_date=start,
                end_date=end,
                platform=Platform.TWITTER,
            )

            asyncio.run(use_case.execute(request, crawler))

            logger.info("crawl_completed", keyword=args.keyword, platform=args.platform)
        finally:
            conn.close()

    except Exception as exc:
        logger.exception("crawl_failed", error=str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
