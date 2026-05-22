"""CLI command to re-enqueue failed AI jobs for reprocessing.

Usage:
    python -m src.infrastructure.ai.retry_jobs [--job-type TYPE]
"""

from __future__ import annotations

import argparse
import sys

import structlog

from src.infrastructure.persistence.duckdb_ai_job_repository import DuckDBAIJobRepository
from src.infrastructure.persistence.migrations import create_all_tables
from src.shared.db_retry import connect_with_retry

logger = structlog.get_logger()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-enqueue failed AI jobs for reprocessing",
    )
    parser.add_argument(
        "--job-type",
        default=None,
        help="Only reset jobs of this type (default: all types)",
    )
    args = parser.parse_args()

    try:
        conn = connect_with_retry()
        try:
            create_all_tables(conn)
            repo = DuckDBAIJobRepository(conn)
            reset_count = repo.reset_failed_jobs(job_type=args.job_type)

            if reset_count == 0:
                logger.info("retry_jobs.no_failed_jobs")
            else:
                logger.info("retry_jobs.reset_complete", reset_count=reset_count)

            logger.info("retry_jobs.result", reset_count=reset_count)
        finally:
            conn.close()

    except Exception as exc:
        logger.exception("retry_jobs.failed", error=str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
