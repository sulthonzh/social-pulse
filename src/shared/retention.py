from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    import duckdb

logger = structlog.get_logger(__name__)

# (schema.table, timestamp_column) — order respects FK dependencies:
# gold first (no FKs pointing to them), then config, silver, bronze.
_PURGE_TABLES: list[tuple[str, str]] = [
    # 1. Gold — leaf tables
    ("gold.gold_post_search", "created_at"),
    ("gold.gold_campaign_daily", "created_at"),
    ("gold.gold_campaign_summary", "created_at"),
    # 2. Config — no FKs into this from other layers
    ("config.gold_build_tracking", "last_built_at"),
    # 3. Silver — ai_jobs / enrichment depend on silver_posts
    ("silver.ai_jobs", "created_at"),
    ("silver.silver_ai_enrichment", "created_at"),
    ("silver.silver_posts", "created_at"),
    # 4. Bronze — leaf of the dependency tree
    ("bronze.bronze_posts", "fetched_at"),
    ("bronze.bronze_crawl_runs", "started_at"),
    ("bronze.search_requests", "created_at"),
]


class DataRetentionService:
    """Purge old records from medallion tables based on configurable TTL."""

    def __init__(self, conn: duckdb.DuckDBPyConnection, retention_days: int = 90) -> None:
        self._conn = conn
        self._retention_days = retention_days

    def purge(self, dry_run: bool = False) -> dict[str, int]:
        """Purge records older than *retention_days* from all layers.

        Returns a dict mapping ``schema.table`` → count of purged rows.
        When *dry_run* is ``True`` the counts are computed via ``SELECT COUNT(*)``
        without actually deleting rows.
        """
        cutoff = datetime.now(UTC) - timedelta(days=self._retention_days)
        results: dict[str, int] = {}

        for table, ts_col in _PURGE_TABLES:
            results[table] = self._purge_table(table, ts_col, cutoff, dry_run)

        logger.info(
            "purge_complete",
            dry_run=dry_run,
            retention_days=self._retention_days,
            total_rows=sum(results.values()),
            results=results,
        )
        return results

    def _purge_table(self, table: str, ts_col: str, cutoff: datetime, dry_run: bool) -> int:
        row = self._conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {ts_col} < ?",
            [cutoff],
        ).fetchone()
        count = row[0] if row is not None else 0

        if not dry_run and count > 0:
            self._conn.execute(
                f"DELETE FROM {table} WHERE {ts_col} < ?",
                [cutoff],
            )

        logger.info("purged_table", table=table, rows=count, dry_run=dry_run)
        return count
