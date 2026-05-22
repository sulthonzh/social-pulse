from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    import duckdb

logger = structlog.get_logger()

_TABLE = "config.gold_build_tracking"


class DuckDBGoldBuildTrackingRepository:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def get_last_build(self, search_request_id: str) -> datetime | None:
        row = self._conn.execute(
            f"SELECT last_built_at FROM {_TABLE} WHERE search_request_id = ?",
            [search_request_id],
        ).fetchone()
        if row is None:
            return None
        raw = row[0]
        return raw if isinstance(raw, datetime) else datetime.fromisoformat(str(raw))

    def record_build(self, search_request_id: str, posts_processed: int) -> None:
        self._conn.execute(
            f"DELETE FROM {_TABLE} WHERE search_request_id = ?",
            [search_request_id],
        )
        self._conn.execute(
            f"""
            INSERT INTO {_TABLE} (search_request_id, last_built_at, posts_processed)
            VALUES (?, current_timestamp, ?)
            """,
            [search_request_id, posts_processed],
        )
        logger.debug(
            "gold_build_tracking.recorded",
            search_request_id=search_request_id,
            posts_processed=posts_processed,
        )

    def get_all_builds(self) -> list[dict[str, object]]:
        rows = self._conn.execute(
            f"SELECT search_request_id, last_built_at, posts_processed FROM {_TABLE} ORDER BY last_built_at DESC"
        ).fetchall()
        return [
            {
                "search_request_id": str(row[0]),
                "last_built_at": str(row[1]),
                "posts_processed": int(str(row[2])),
            }
            for row in rows
        ]
