from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb
import pytest
from src.shared.backup import backup_database

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    db_file = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_file))
    conn.execute("CREATE TABLE t (id INTEGER)")
    conn.execute("INSERT INTO t VALUES (1), (2), (3)")
    conn.close()
    return db_file


def test_backup_creates_file_in_backup_dir(tmp_db: Path, tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    result = backup_database(str(tmp_db), str(backup_dir))
    assert result.exists()
    assert result.parent == backup_dir


def test_backup_filename_contains_timestamp(tmp_db: Path, tmp_path: Path) -> None:
    result = backup_database(str(tmp_db), str(tmp_path / "backups"))
    name = result.name
    assert name.startswith("socialpulse_")
    assert name.endswith(".duckdb")
    middle = name[len("socialpulse_") : -len(".duckdb")]
    parts = middle.split("_")
    assert len(parts) == 2
    assert len(parts[0]) == 8
    assert len(parts[1]) == 6


def test_backup_preserves_file_size(tmp_db: Path, tmp_path: Path) -> None:
    result = backup_database(str(tmp_db), str(tmp_path / "backups"))
    original_size = tmp_db.stat().st_size
    backup_size = result.stat().st_size
    assert backup_size == original_size


def test_backup_creates_directory_if_not_exists(tmp_db: Path, tmp_path: Path) -> None:
    nested = tmp_path / "deep" / "nested" / "backups"
    assert not nested.exists()
    result = backup_database(str(tmp_db), str(nested))
    assert nested.exists()
    assert result.exists()


def test_backup_handles_missing_source_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Database file not found"):
        backup_database(str(tmp_path / "nonexistent.duckdb"), str(tmp_path / "backups"))


def test_backup_with_sql_export(tmp_db: Path, tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    result = backup_database(str(tmp_db), str(backup_dir), export_sql=True)
    assert result.exists()

    sql_dirs = list(backup_dir.glob("*_sql"))
    assert len(sql_dirs) == 1
    assert sql_dirs[0].is_dir()

    exported_files = list(sql_dirs[0].iterdir())
    assert any(f.name == "schema.sql" for f in exported_files)
