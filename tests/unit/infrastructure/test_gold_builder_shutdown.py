from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import duckdb
import pytest
from src.infrastructure.gold.builder import GoldBuilder
from src.infrastructure.persistence.migrations import create_all_tables


@pytest.fixture
def conn() -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect(":memory:")
    create_all_tables(connection)
    yield connection
    connection.close()


def _insert_completed_request(
    conn: duckdb.DuckDBPyConnection,
    keyword: str = "test",
    platform: str = "twitter",
) -> str:
    sid = str(uuid4())
    now = datetime.now(UTC)
    conn.execute(
        "INSERT INTO bronze.search_requests "
        "(id, keyword, start_date, end_date, platform, status, posts_found, created_at, updated_at) "
        "VALUES (?, ?, '2025-01-01', '2025-01-31', ?, 'completed', 0, ?, ?)",
        [sid, keyword, platform, now, now],
    )
    return sid


class TestGoldBuilderShutdown:
    @pytest.mark.asyncio
    async def test_stops_mid_batch_when_shutdown_set(self, conn: duckdb.DuckDBPyConnection) -> None:
        for i in range(5):
            _insert_completed_request(conn, keyword=f"kw-{i}")

        builder = GoldBuilder(conn)
        builder._shutdown_event.set()

        await builder.run()

        rows = conn.execute("SELECT COUNT(*) FROM gold.gold_post_search").fetchone()
        assert rows is not None and rows[0] == 0

    @pytest.mark.asyncio
    async def test_request_shutdown_sets_event(self, conn: duckdb.DuckDBPyConnection) -> None:
        builder = GoldBuilder(conn)
        assert not builder._shutdown_event.is_set()
        builder.request_shutdown()
        assert builder._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_processes_when_shutdown_not_set(self, conn: duckdb.DuckDBPyConnection) -> None:
        _insert_completed_request(conn, keyword="shutdown-test")

        builder = GoldBuilder(conn)

        assert not builder._shutdown_event.is_set()
        await builder.run()
