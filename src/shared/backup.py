"""DuckDB backup utility — file copy + optional SQL export + rotation."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timedelta
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


def rotate_backups(
    backup_dir: str = "data/backups",
    max_backups: int = 7,
    max_age_days: int = 30,
) -> int:
    """Delete backups that exceed the retention policy.

    Backups are sorted newest-first. Any backup beyond ``max_backups`` count
    OR older than ``max_age_days`` is removed.

    Args:
        backup_dir: Directory containing backup files.
        max_backups: Maximum number of backups to keep.
        max_age_days: Maximum age in days for any single backup.

    Returns:
        Number of backups deleted.
    """
    dest_dir = Path(backup_dir)
    if not dest_dir.exists():
        return 0

    cutoff = datetime.now() - timedelta(days=max_age_days)
    backups = sorted(
        dest_dir.glob("socialpulse_*.duckdb"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    deleted = 0
    for i, path in enumerate(backups):
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        beyond_count = i >= max_backups
        beyond_age = mtime < cutoff

        if beyond_count or beyond_age:
            size_mb = path.stat().st_size / (1024 * 1024)
            path.unlink()
            deleted += 1
            logger.info(
                "backup_rotated",
                path=str(path),
                size_mb=round(size_mb, 2),
                reason="count_exceeded" if beyond_count else "age_exceeded",
            )

            sql_dir = Path(str(path).removesuffix(".duckdb") + "_sql")
            if sql_dir.exists():
                shutil.rmtree(sql_dir)

    if deleted:
        logger.info("backup_rotation_complete", deleted=deleted, remaining=len(backups) - deleted)
    return deleted


def scheduled_backup(
    db_path: str,
    backup_dir: str = "data/backups",
    max_backups: int = 7,
    max_age_days: int = 30,
    export_sql: bool = False,
) -> Path:
    """Run a backup followed by rotation.

    Args:
        db_path: Path to the DuckDB database file.
        backup_dir: Directory to store backups.
        max_backups: Maximum number of backups to keep after rotation.
        max_age_days: Maximum age in days for backups after rotation.
        export_sql: If True, also export backup as SQL dump.

    Returns:
        Path to the newly created backup file.
    """
    backup_path = backup_database(db_path, backup_dir, export_sql=export_sql)
    rotate_backups(backup_dir, max_backups=max_backups, max_age_days=max_age_days)
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
    parser.add_argument(
        "--max-backups",
        type=int,
        default=7,
        help="Maximum number of backups to keep (default: 7)",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=30,
        help="Maximum backup age in days (default: 30)",
    )
    parser.add_argument(
        "--rotate",
        action="store_true",
        default=False,
        help="Rotate backups after creating a new one",
    )
    args = parser.parse_args()

    if args.rotate:
        path = scheduled_backup(
            db_path=args.db_path,
            backup_dir=args.backup_dir,
            max_backups=args.max_backups,
            max_age_days=args.max_age_days,
            export_sql=args.export_sql,
        )
    else:
        path = backup_database(
            db_path=args.db_path,
            backup_dir=args.backup_dir,
            export_sql=args.export_sql,
        )
    print(f"Backup created: {path}")


if __name__ == "__main__":
    main()
