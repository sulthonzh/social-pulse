from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb

if TYPE_CHECKING:
    from collections.abc import Generator
import pytest
from src.infrastructure.persistence.migrations import (
    SCHEMA_VERSION,
    create_all_tables,
    run_migrations,
)


@pytest.fixture
def conn() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    connection = duckdb.connect(":memory:")
    create_all_tables(connection)
    yield connection
    connection.close()


def test_schema_version_is_5() -> None:
    assert SCHEMA_VERSION == 5


@pytest.mark.parametrize(
    "table",
    ["gold.gold_post_search", "gold.gold_campaign_daily", "gold.gold_campaign_summary"],
)
def test_migration_v5_adds_lineage_columns(conn: duckdb.DuckDBPyConnection, table: str) -> None:
    for col in ("source_crawl_run_id", "enrichment_job_id", "lineage_updated_at"):
        row = conn.execute(
            "SELECT COUNT(*) FROM information_schema.columns"
            " WHERE table_name = ? AND column_name = ?",
            [table.split(".")[1], col],
        ).fetchone()
        assert row is not None and row[0] == 1, f"Column {col} missing from {table}"


def test_migration_v5_is_idempotent(conn: duckdb.DuckDBPyConnection) -> None:
    run_migrations(conn)
    run_migrations(conn)

    row = conn.execute(
        "SELECT COUNT(*) FROM config.schema_migrations WHERE version = 5",
    ).fetchone()
    assert row is not None and row[0] == 1


def test_migration_v5_recorded_in_schema_migrations(conn: duckdb.DuckDBPyConnection) -> None:
    row = conn.execute(
        "SELECT description FROM config.schema_migrations WHERE version = 5",
    ).fetchone()
    assert row is not None
    assert "lineage" in row[0]
