"""DuckDB connection retry utility with exponential backoff.

Handles IOException caused by database lock contention between
concurrent processes (workers, API, Streamlit).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import structlog

from src.shared.config import settings

if TYPE_CHECKING:
    import duckdb

logger = structlog.get_logger()


def connect_with_retry(
    db_path: str | None = None,
    max_retries: int = 5,
    base_delay: float = 2.0,
) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection, retrying with exponential backoff on lock errors.

    Args:
        db_path: Path to the DuckDB database file. Defaults to settings.db_path.
        max_retries: Maximum number of connection attempts.
        base_delay: Base delay in seconds for exponential backoff.

    Returns:
        An open DuckDB connection.

    Raises:
        duckdb.IOException: If the lock persists after all retries.
        RuntimeError: If all retries are exhausted.
    """
    import duckdb  # noqa: PLC0415

    path = db_path or settings.db_path

    for attempt in range(1, max_retries + 1):
        try:
            return duckdb.connect(path)
        except duckdb.IOException as exc:
            if "lock" not in str(exc).lower() or attempt == max_retries:
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "db_locked_retry",
                attempt=attempt,
                max_retries=max_retries,
                delay=delay,
            )
            time.sleep(delay)

    raise RuntimeError("Failed to acquire DuckDB lock after retries")
