from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from src.domain.entities.ai_job import AIJob
from src.domain.value_objects.ai_job_status import AIJobStatus
from src.domain.value_objects.ai_job_type import AIJobType

if TYPE_CHECKING:
    import duckdb

logger = structlog.get_logger()

_TABLE = "silver.ai_jobs"

_INSERT_COLUMNS = (
    "id, silver_post_id, job_type, status, ai_version, "
    "attempts, max_attempts, error_message, started_at, completed_at, created_at"
)

_SELECT_COLUMNS = _INSERT_COLUMNS


def _resolve_uuid(raw: object) -> UUID:
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def _resolve_datetime(raw: object) -> datetime | None:
    if raw is None:
        return None
    return raw if isinstance(raw, datetime) else datetime.fromisoformat(str(raw))


def _resolve_str(raw: object) -> str | None:
    return str(raw) if raw is not None else None


def _row_to_ai_job(row: tuple[object, ...]) -> AIJob:
    (
        raw_id,
        raw_silver_post_id,
        raw_job_type,
        raw_status,
        raw_ai_version,
        raw_attempts,
        raw_max_attempts,
        raw_error_message,
        raw_started_at,
        raw_completed_at,
        raw_created_at,
    ) = row

    return AIJob(
        id=_resolve_uuid(raw_id),
        silver_post_id=_resolve_uuid(raw_silver_post_id),
        job_type=AIJobType(str(raw_job_type)),
        status=AIJobStatus(str(raw_status)),
        ai_version=int(str(raw_ai_version)),
        attempts=int(str(raw_attempts)),
        max_attempts=int(str(raw_max_attempts)),
        error_message=_resolve_str(raw_error_message),
        started_at=_resolve_datetime(raw_started_at),
        completed_at=_resolve_datetime(raw_completed_at),
        created_at=_resolve_datetime(raw_created_at) or datetime.now(),
    )


def _job_to_params(job: AIJob) -> tuple[object, ...]:
    return (
        str(job.id),
        str(job.silver_post_id),
        job.job_type.value,
        job.status.value,
        job.ai_version,
        job.attempts,
        job.max_attempts,
        job.error_message,
        job.started_at,
        job.completed_at,
        job.created_at,
    )


class DuckDBAIJobRepository:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def save(self, job: AIJob) -> AIJob:
        self._conn.execute(
            f"""
            INSERT INTO {_TABLE}
                ({_INSERT_COLUMNS})
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            list(_job_to_params(job)),
        )
        logger.debug(
            "ai_job.saved",
            job_id=str(job.id),
            job_type=job.job_type.value,
        )
        return job

    def get_pending_jobs(self, job_type: str | None = None, limit: int = 100) -> list[AIJob]:
        if job_type is not None:
            rows = self._conn.execute(
                f"""
                SELECT {_SELECT_COLUMNS}
                FROM {_TABLE}
                WHERE status = 'pending' AND job_type = ?
                ORDER BY created_at
                LIMIT ?
                """,
                [job_type, limit],
            ).fetchall()
        else:
            rows = self._conn.execute(
                f"""
                SELECT {_SELECT_COLUMNS}
                FROM {_TABLE}
                WHERE status = 'pending'
                ORDER BY created_at
                LIMIT ?
                """,
                [limit],
            ).fetchall()
        return [_row_to_ai_job(row) for row in rows]

    def update_status(
        self,
        job_id: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        if status == "running":
            self._conn.execute(
                f"""
                UPDATE {_TABLE}
                SET status = ?,
                    error_message = ?,
                    started_at = current_timestamp
                WHERE id = ?
                """,
                [status, error_message, job_id],
            )
        elif status in ("completed", "failed"):
            self._conn.execute(
                f"""
                UPDATE {_TABLE}
                SET status = ?,
                    error_message = ?,
                    completed_at = current_timestamp
                WHERE id = ?
                """,
                [status, error_message, job_id],
            )
        else:
            self._conn.execute(
                f"""
                UPDATE {_TABLE}
                SET status = ?,
                    error_message = ?
                WHERE id = ?
                """,
                [status, error_message, job_id],
            )
        logger.debug(
            "ai_job.status_updated",
            job_id=job_id,
            status=status,
        )

    def update_attempts(self, job_id: str, attempts: int) -> None:
        self._conn.execute(
            f"UPDATE {_TABLE} SET attempts = ? WHERE id = ?",
            [attempts, job_id],
        )

    def reset_failed_jobs(self, job_type: str | None = None) -> int:
        if job_type is not None:
            row = self._conn.execute(
                f"SELECT count(*) FROM {_TABLE} WHERE status = 'failed' AND job_type = ?",
                [job_type],
            ).fetchone()
            self._conn.execute(
                f"""
                UPDATE {_TABLE}
                SET status = 'pending',
                    error_message = NULL,
                    started_at = NULL,
                    completed_at = NULL
                WHERE status = 'failed' AND job_type = ?
                """,
                [job_type],
            )
        else:
            row = self._conn.execute(
                f"SELECT count(*) FROM {_TABLE} WHERE status = 'failed'",
            ).fetchone()
            self._conn.execute(
                f"""
                UPDATE {_TABLE}
                SET status = 'pending',
                    error_message = NULL,
                    started_at = NULL,
                    completed_at = NULL
                WHERE status = 'failed'
                """,
            )

        reset_count = int(str(row[0])) if row is not None else 0
        logger.info(
            "ai_jobs.reset_failed",
            reset_count=reset_count,
            job_type=job_type,
        )
        return reset_count
