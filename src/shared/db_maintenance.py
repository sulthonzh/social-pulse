"""DuckDB maintenance utilities — checkpoint, vacuum, and analyze."""

from __future__ import annotations

import argparse
from pathlib import Path

import structlog

from src.shared.config import settings

logger = structlog.get_logger(__name__)


def run_checkpoint(db_path: str) -> bool:
    """Force a WAL checkpoint on the database.

    Args:
        db_path: Path to the DuckDB database file.

    Returns:
        True if checkpoint succeeded, False otherwise.
    """
    source = Path(db_path)
    if not source.exists():
        logger.error("checkpoint_failed", error="database file not found", path=db_path)
        return False

    import duckdb  # noqa: PLC0415

    try:
        conn = duckdb.connect(str(source))
        try:
            conn.execute("FORCE CHECKPOINT")
            logger.info("checkpoint_complete", path=db_path)
            return True
        finally:
            conn.close()
    except Exception:
        logger.exception("checkpoint_failed", path=db_path)
        return False


def run_vacuum(db_path: str) -> bool:
    """Reclaim space by running VACUUM followed by ANALYZE.

    Args:
        db_path: Path to the DuckDB database file.

    Returns:
        True if vacuum succeeded, False otherwise.
    """
    source = Path(db_path)
    if not source.exists():
        logger.error("vacuum_failed", error="database file not found", path=db_path)
        return False

    import duckdb  # noqa: PLC0415

    try:
        conn = duckdb.connect(str(source))
        try:
            conn.execute("VACUUM")
            logger.info("vacuum_complete", path=db_path)
            conn.execute("ANALYZE")
            logger.info("post_vacuum_analyze_complete", path=db_path)
            return True
        finally:
            conn.close()
    except Exception:
        logger.exception("vacuum_failed", path=db_path)
        return False


def run_analyze(db_path: str) -> bool:
    """Update table statistics for query optimization.

    Args:
        db_path: Path to the DuckDB database file.

    Returns:
        True if analyze succeeded, False otherwise.
    """
    source = Path(db_path)
    if not source.exists():
        logger.error("analyze_failed", error="database file not found", path=db_path)
        return False

    import duckdb  # noqa: PLC0415

    try:
        conn = duckdb.connect(str(source))
        try:
            conn.execute("ANALYZE")
            logger.info("analyze_complete", path=db_path)
            return True
        finally:
            conn.close()
    except Exception:
        logger.exception("analyze_failed", path=db_path)
        return False


def run_all_maintenance(db_path: str) -> dict[str, bool]:
    """Run all maintenance operations in order: checkpoint, vacuum, analyze.

    Args:
        db_path: Path to the DuckDB database file.

    Returns:
        Dictionary mapping operation names to their success status.
    """
    results: dict[str, bool] = {}

    logger.info("maintenance_started", path=db_path)

    results["checkpoint"] = run_checkpoint(db_path)
    results["vacuum"] = run_vacuum(db_path)
    results["analyze"] = run_analyze(db_path)

    succeeded = sum(1 for v in results.values() if v)
    total = len(results)
    logger.info("maintenance_complete", succeeded=succeeded, total=total, results=results)

    return results


def main() -> None:
    """CLI entry point for socialpulse-maintenance."""
    parser = argparse.ArgumentParser(
        description="Run DuckDB maintenance operations (checkpoint, vacuum, analyze).",
    )
    parser.add_argument(
        "db_path",
        nargs="?",
        default=settings.db_path,
        help=f"Path to the DuckDB database file (default: {settings.db_path})",
    )
    parser.add_argument(
        "--operation",
        choices=["checkpoint", "vacuum", "analyze", "all"],
        default="all",
        help="Maintenance operation to run (default: all)",
    )
    args = parser.parse_args()

    operation = args.operation
    if operation == "all":
        results = run_all_maintenance(args.db_path)
        for name, ok in results.items():
            status = "OK" if ok else "FAILED"
            print(f"  {name}: {status}")
    elif operation == "checkpoint":
        ok = run_checkpoint(args.db_path)
        print(f"checkpoint: {'OK' if ok else 'FAILED'}")
    elif operation == "vacuum":
        ok = run_vacuum(args.db_path)
        print(f"vacuum: {'OK' if ok else 'FAILED'}")
    elif operation == "analyze":
        ok = run_analyze(args.db_path)
        print(f"analyze: {'OK' if ok else 'FAILED'}")


if __name__ == "__main__":
    main()
