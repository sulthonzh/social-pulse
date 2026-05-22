from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import duckdb
import pytest
from src.infrastructure.persistence.migrations import create_all_tables
from src.shared.retention import DataRetentionService


@pytest.fixture
def conn() -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect(":memory:")
    create_all_tables(connection)
    yield connection
    connection.close()


def _insert_search_request(conn: duckdb.DuckDBPyConnection, **overrides: object) -> str:
    sid = str(uuid4())
    defaults: dict[str, object] = {
        "id": sid,
        "keyword": "test",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "platform": "twitter",
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    cols = ", ".join(defaults.keys())
    placeholders = ", ".join("?" for _ in defaults)
    conn.execute(f"INSERT INTO bronze.search_requests ({cols}) VALUES ({placeholders})", list(defaults.values()))
    return sid


def _insert_crawl_run(conn: duckdb.DuckDBPyConnection, search_request_id: str, **overrides: object) -> str:
    rid = str(uuid4())
    defaults: dict[str, object] = {
        "id": rid,
        "search_request_id": search_request_id,
        "platform": "twitter",
        "started_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    cols = ", ".join(defaults.keys())
    placeholders = ", ".join("?" for _ in defaults)
    conn.execute(f"INSERT INTO bronze.bronze_crawl_runs ({cols}) VALUES ({placeholders})", list(defaults.values()))
    return rid


def _insert_bronze_post(
    conn: duckdb.DuckDBPyConnection, search_request_id: str, crawl_run_id: str, **overrides: object
) -> str:
    pid = str(uuid4())
    defaults: dict[str, object] = {
        "id": pid,
        "search_request_id": search_request_id,
        "crawl_run_id": crawl_run_id,
        "platform": "twitter",
        "fetched_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    cols = ", ".join(defaults.keys())
    placeholders = ", ".join("?" for _ in defaults)
    conn.execute(f"INSERT INTO bronze.bronze_posts ({cols}) VALUES ({placeholders})", list(defaults.values()))
    return pid


def _insert_gold_post_search(conn: duckdb.DuckDBPyConnection, **overrides: object) -> str:
    gid = str(uuid4())
    defaults: dict[str, object] = {
        "id": gid,
        "search_request_id": str(uuid4()),
        "keyword": "test",
        "platform": "twitter",
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    cols = ", ".join(defaults.keys())
    placeholders = ", ".join("?" for _ in defaults)
    conn.execute(f"INSERT INTO gold.gold_post_search ({cols}) VALUES ({placeholders})", list(defaults.values()))
    return gid


def test_purge_dry_run_returns_counts_without_deleting(conn: duckdb.DuckDBPyConnection) -> None:
    old_ts = datetime.now(UTC) - timedelta(days=200)
    _insert_gold_post_search(conn, created_at=old_ts)
    _insert_gold_post_search(conn, created_at=old_ts)

    service = DataRetentionService(conn, retention_days=90)
    counts = service.purge(dry_run=True)

    assert counts["gold.gold_post_search"] == 2

    total = conn.execute("SELECT COUNT(*) FROM gold.gold_post_search").fetchone()
    assert total is not None and total[0] == 2


def test_purge_deletes_old_records(conn: duckdb.DuckDBPyConnection) -> None:
    old_ts = datetime.now(UTC) - timedelta(days=200)
    recent_ts = datetime.now(UTC) - timedelta(days=5)

    _insert_gold_post_search(conn, created_at=old_ts)
    _insert_gold_post_search(conn, created_at=old_ts)
    _insert_gold_post_search(conn, created_at=recent_ts)

    service = DataRetentionService(conn, retention_days=90)
    counts = service.purge(dry_run=False)

    assert counts["gold.gold_post_search"] == 2

    remaining = conn.execute("SELECT COUNT(*) FROM gold.gold_post_search").fetchone()
    assert remaining is not None and remaining[0] == 1


def test_purge_respects_retention_days(conn: duckdb.DuckDBPyConnection) -> None:
    ts_30d = datetime.now(UTC) - timedelta(days=30)
    ts_60d = datetime.now(UTC) - timedelta(days=60)
    ts_120d = datetime.now(UTC) - timedelta(days=120)

    _insert_gold_post_search(conn, created_at=ts_30d)
    _insert_gold_post_search(conn, created_at=ts_60d)
    _insert_gold_post_search(conn, created_at=ts_120d)

    service_90 = DataRetentionService(conn, retention_days=90)
    counts_90 = service_90.purge(dry_run=False)
    assert counts_90["gold.gold_post_search"] == 1

    remaining = conn.execute("SELECT COUNT(*) FROM gold.gold_post_search").fetchone()
    assert remaining is not None and remaining[0] == 2


def test_purge_empty_database(conn: duckdb.DuckDBPyConnection) -> None:
    service = DataRetentionService(conn, retention_days=90)
    counts = service.purge(dry_run=False)

    assert all(v == 0 for v in counts.values())
    assert len(counts) == 10


def test_purge_across_multiple_layers(conn: duckdb.DuckDBPyConnection) -> None:
    old_ts = datetime.now(UTC) - timedelta(days=200)
    recent_ts = datetime.now(UTC) - timedelta(days=5)

    sr_id_old = _insert_search_request(conn, created_at=old_ts)
    cr_id_old = _insert_crawl_run(conn, sr_id_old, started_at=old_ts)
    _insert_bronze_post(conn, sr_id_old, cr_id_old, fetched_at=old_ts)

    sr_id_new = _insert_search_request(conn, created_at=recent_ts)
    cr_id_new = _insert_crawl_run(conn, sr_id_new, started_at=recent_ts)
    _insert_bronze_post(conn, sr_id_new, cr_id_new, fetched_at=recent_ts)

    _insert_gold_post_search(conn, created_at=old_ts)
    _insert_gold_post_search(conn, created_at=recent_ts)

    service = DataRetentionService(conn, retention_days=90)
    counts = service.purge(dry_run=False)

    assert counts["gold.gold_post_search"] == 1
    assert counts["bronze.bronze_posts"] == 1
    assert counts["bronze.bronze_crawl_runs"] == 1
    assert counts["bronze.search_requests"] == 1

    sr_remaining = conn.execute("SELECT COUNT(*) FROM bronze.search_requests").fetchone()
    assert sr_remaining is not None and sr_remaining[0] == 1
