from __future__ import annotations

import argparse
import sys

import structlog

from src.shared.config import settings

logger = structlog.get_logger()


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge old records from SocialPulse")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Show counts without deleting")
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help=f"Retention window in days (default: {settings.retention_days})",
    )

    args = parser.parse_args()
    retention_days = args.days if args.days is not None else settings.retention_days

    try:
        import duckdb  # noqa: PLC0415

        from src.infrastructure.persistence.migrations import create_all_tables  # noqa: PLC0415
        from src.shared.retention import DataRetentionService  # noqa: PLC0415

        conn = duckdb.connect(settings.db_path)
        try:
            create_all_tables(conn)
            service = DataRetentionService(conn, retention_days=retention_days)
            counts = service.purge(dry_run=args.dry_run)
            logger.info("purge_complete", dry_run=args.dry_run, results=counts)
        finally:
            conn.close()

    except Exception as exc:
        logger.exception("purge_failed", error=str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
