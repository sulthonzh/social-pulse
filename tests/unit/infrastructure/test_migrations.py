from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from src.infrastructure.persistence.migrations import (
    SCHEMA_VERSION,
    _create_config_schema,
    create_all_tables,
    get_applied_version,
    rollback_migration,
    run_migrations,
)

if TYPE_CHECKING:
    import duckdb


@pytest.mark.unit
class TestForwardMigrations:
    def test_all_migrations_applied_on_fresh_db(
        self, db_connection: duckdb.DuckDBPyConnection
    ) -> None:
        create_all_tables(db_connection)
        assert get_applied_version(db_connection) == SCHEMA_VERSION

    def test_schema_migrations_populated(self, db_connection: duckdb.DuckDBPyConnection) -> None:
        create_all_tables(db_connection)
        rows = db_connection.execute(
            "SELECT version FROM config.schema_migrations ORDER BY version"
        ).fetchall()
        versions = [r[0] for r in rows]
        assert versions == [2, 3, 4, 5]

    def test_run_migrations_idempotent(self, db_connection: duckdb.DuckDBPyConnection) -> None:
        create_all_tables(db_connection)
        run_migrations(db_connection)
        rows = db_connection.execute("SELECT COUNT(*) FROM config.schema_migrations").fetchone()
        assert rows is not None
        assert rows[0] == 4

    def test_gold_build_tracking_exists(self, db_connection: duckdb.DuckDBPyConnection) -> None:
        create_all_tables(db_connection)
        result = db_connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables"
            " WHERE table_schema='config' AND table_name='gold_build_tracking'"
        ).fetchone()
        assert result is not None
        assert result[0] == 1


@pytest.mark.unit
class TestGetAppliedVersion:
    def test_returns_1_when_no_migrations(self, db_connection: duckdb.DuckDBPyConnection) -> None:
        _create_config_schema(db_connection)
        assert get_applied_version(db_connection) == 1

    def test_returns_max_applied_version(self, db_connection: duckdb.DuckDBPyConnection) -> None:
        create_all_tables(db_connection)
        assert get_applied_version(db_connection) == 5


@pytest.mark.unit
class TestRollbackMigration:
    def test_rollback_to_v3_removes_v4_indexes(
        self, db_connection: duckdb.DuckDBPyConnection
    ) -> None:
        create_all_tables(db_connection)
        rollback_migration(db_connection, target_version=3)
        assert get_applied_version(db_connection) == 3
        rows = db_connection.execute(
            "SELECT version FROM config.schema_migrations ORDER BY version"
        ).fetchall()
        versions = [r[0] for r in rows]
        assert versions == [2, 3]

    def test_rollback_to_v2_removes_v3_and_v4(
        self, db_connection: duckdb.DuckDBPyConnection
    ) -> None:
        create_all_tables(db_connection)
        rollback_migration(db_connection, target_version=2)
        assert get_applied_version(db_connection) == 2
        rows = db_connection.execute(
            "SELECT version FROM config.schema_migrations ORDER BY version"
        ).fetchall()
        versions = [r[0] for r in rows]
        assert versions == [2]
        result = db_connection.execute(
            "SELECT COUNT(*) FROM information_schema.tables"
            " WHERE table_schema='config' AND table_name='gold_build_tracking'"
        ).fetchone()
        assert result is not None
        assert result[0] == 0

    def test_rollback_to_v1_removes_all(self, db_connection: duckdb.DuckDBPyConnection) -> None:
        create_all_tables(db_connection)
        rollback_migration(db_connection, target_version=1)
        assert get_applied_version(db_connection) == 1
        rows = db_connection.execute("SELECT COUNT(*) FROM config.schema_migrations").fetchone()
        assert rows is not None
        assert rows[0] == 0

    def test_rollback_with_invalid_target_raises(
        self, db_connection: duckdb.DuckDBPyConnection
    ) -> None:
        with pytest.raises(ValueError, match="target_version must be >= 1"):
            rollback_migration(db_connection, target_version=0)

    def test_rollback_when_already_at_target_is_noop(
        self, db_connection: duckdb.DuckDBPyConnection
    ) -> None:
        create_all_tables(db_connection)
        rollback_migration(db_connection, target_version=SCHEMA_VERSION)
        assert get_applied_version(db_connection) == SCHEMA_VERSION

    def test_rerun_migrations_after_rollback(
        self, db_connection: duckdb.DuckDBPyConnection
    ) -> None:
        create_all_tables(db_connection)
        rollback_migration(db_connection, target_version=2)
        run_migrations(db_connection)
        assert get_applied_version(db_connection) == SCHEMA_VERSION
