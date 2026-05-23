from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb

if TYPE_CHECKING:
    from collections.abc import Generator
import pytest
from src.infrastructure.persistence.migrations import (
    create_all_tables,
    run_migrations,
)


@pytest.fixture
def conn() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    connection = duckdb.connect(":memory:")
    create_all_tables(connection)
    yield connection
    connection.close()


def test_migration_v4_creates_expected_indexes(conn: duckdb.DuckDBPyConnection) -> None:
    expected_indexes = [
        "idx_silver_posts_created_at",
        "idx_silver_enrichment_created_at",
        "idx_gold_post_search_created_at",
        "idx_gold_campaign_daily_created_at",
    ]
    for idx_name in expected_indexes:
        row = conn.execute(
            "SELECT COUNT(*) FROM duckdb_indexes() WHERE index_name = ?",
            [idx_name],
        ).fetchone()
        assert row is not None and row[0] >= 1, f"Index {idx_name} not found"


def test_migration_v4_is_idempotent(conn: duckdb.DuckDBPyConnection) -> None:
    run_migrations(conn)
    run_migrations(conn)

    row = conn.execute(
        "SELECT COUNT(*) FROM config.schema_migrations WHERE version = 4",
    ).fetchone()
    assert row is not None and row[0] == 1


def test_migration_v4_recorded_in_schema_migrations(conn: duckdb.DuckDBPyConnection) -> None:
    row = conn.execute(
        "SELECT description FROM config.schema_migrations WHERE version = 4",
    ).fetchone()
    assert row is not None
    assert "time-based indexes" in row[0]
