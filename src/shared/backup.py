"""DuckDB backup utility — file copy + optional SQL export."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


def backup_database(
    db_path: str,
    backup_dir: str = "data/backups",
    export_sql: bool = False,
) -> Path:
    """Create a timestamped backup of the DuckDB database.

    Args:
        db_path: Path to the DuckDB database file.
        backup_dir: Directory to store backups.
        export_sql: If True, also export as SQL dump.

    Returns:
        Path to the backup file.

    Raises:
        FileNotFoundError: If db_path does not exist.
    """
    source = Path(db_path)
    if not source.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")

    dest_dir = Path(backup_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"socialpulse_{timestamp}.duckdb"
    backup_path = dest_dir / backup_name

    shutil.copy2(source, backup_path)

    size_mb = backup_path.stat().st_size / (1024 * 1024)
    logger.info("backup_created", path=str(backup_path), size_mb=round(size_mb, 2))

    if export_sql:
        import duckdb  # noqa: PLC0415

        sql_dir = dest_dir / f"socialpulse_{timestamp}_sql"
        conn = duckdb.connect(str(backup_path), read_only=True)
        try:
            conn.execute(f"EXPORT DATABASE '{sql_dir}'")
            logger.info("backup_sql_exported", path=str(sql_dir))
        finally:
            conn.close()

    return backup_path


def main() -> None:
    """CLI entry point for socialpulse-backup."""
    parser = argparse.ArgumentParser(
        description="Create a timestamped backup of the SocialPulse DuckDB database.",
    )
    parser.add_argument(
        "db_path",
        nargs="?",
        default="data/socialpulse.duckdb",
        help="Path to the DuckDB database file (default: data/socialpulse.duckdb)",
    )
    parser.add_argument(
        "--backup-dir",
        default="data/backups",
        help="Directory to store backups (default: data/backups)",
    )
    parser.add_argument(
        "--export-sql",
        action="store_true",
        default=False,
        help="Also export backup as SQL dump",
    )
    args = parser.parse_args()

    path = backup_database(
        db_path=args.db_path,
        backup_dir=args.backup_dir,
        export_sql=args.export_sql,
    )
    print(f"Backup created: {path}")


if __name__ == "__main__":
    main()
