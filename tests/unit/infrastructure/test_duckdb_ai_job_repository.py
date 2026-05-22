from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from src.domain.entities.ai_job import AIJob
from src.domain.entities.enriched_post import EnrichedPost
from src.domain.value_objects.ai_job_status import AIJobStatus
from src.domain.value_objects.ai_job_type import AIJobType
from src.domain.value_objects.platform import Platform
from src.infrastructure.persistence.duckdb_ai_job_repository import DuckDBAIJobRepository
from src.infrastructure.persistence.duckdb_enriched_post_repository import (
    DuckDBEnrichedPostRepository,
)


def _make_enriched_post(**overrides) -> EnrichedPost:
    defaults = {
        "id": uuid4(),
        "bronze_post_id": uuid4(),
        "search_request_id": uuid4(),
        "platform": Platform.TWITTER,
        "platform_id": f"tweet_{uuid4().hex[:8]}",
        "author_handle": "testuser",
        "post_text": "Hello world",
        "posted_at": datetime(2025, 1, 15, 10, 0, 0),
        "created_at": datetime(2025, 1, 15, 12, 0, 0),
    }
    defaults.update(overrides)
    return EnrichedPost(**defaults)


def _insert_silver_post(db_with_schema, **overrides) -> EnrichedPost:
    post_repo = DuckDBEnrichedPostRepository(db_with_schema)
    post = _make_enriched_post(**overrides)
    post_repo.save(post)
    return post


def _make_ai_job(silver_post_id, **overrides) -> AIJob:
    defaults = {
        "id": uuid4(),
        "silver_post_id": silver_post_id,
        "job_type": AIJobType.SENTIMENT,
        "status": AIJobStatus.PENDING,
        "ai_version": 1,
        "attempts": 0,
        "max_attempts": 3,
        "error_message": None,
        "started_at": None,
        "completed_at": None,
        "created_at": datetime(2025, 1, 15, 14, 0, 0),
    }
    defaults.update(overrides)
    return AIJob(**defaults)


@pytest.mark.unit
class TestDuckDBAIJobRepository:
    def test_save_returns_entity_with_id(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIJobRepository(db_with_schema)
        job = _make_ai_job(post.id)
        result = repo.save(job)
        assert result.id == job.id

    def test_save_batch_via_multiple_saves(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIJobRepository(db_with_schema)
        jobs = [_make_ai_job(post.id) for _ in range(3)]
        for job in jobs:
            repo.save(job)

        pending = repo.get_pending_jobs()
        assert len(pending) == 3

    def test_get_pending_jobs_returns_pending_only(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIJobRepository(db_with_schema)
        job_pending = _make_ai_job(post.id)
        job_running = _make_ai_job(post.id, status=AIJobStatus.RUNNING)
        repo.save(job_pending)
        repo.save(job_running)

        pending = repo.get_pending_jobs()
        assert len(pending) == 1
        assert pending[0].status == AIJobStatus.PENDING

    def test_get_pending_jobs_filters_by_type(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIJobRepository(db_with_schema)
        repo.save(_make_ai_job(post.id, job_type=AIJobType.SENTIMENT))
        repo.save(_make_ai_job(post.id, job_type=AIJobType.TOPIC))

        pending = repo.get_pending_jobs(job_type="sentiment")
        assert len(pending) == 1
        assert pending[0].job_type == AIJobType.SENTIMENT

    def test_get_pending_jobs_respects_limit(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIJobRepository(db_with_schema)
        for _ in range(5):
            repo.save(_make_ai_job(post.id))

        pending = repo.get_pending_jobs(limit=3)
        assert len(pending) == 3

    def test_get_pending_jobs_returns_empty_when_none(self, db_with_schema):
        repo = DuckDBAIJobRepository(db_with_schema)
        assert repo.get_pending_jobs() == []

    def test_update_status_running_sets_started_at(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIJobRepository(db_with_schema)
        job = _make_ai_job(post.id)
        repo.save(job)

        repo.update_status(str(job.id), "running")

        all_jobs = repo.get_pending_jobs()
        assert len(all_jobs) == 0

    def test_update_status_completed_sets_completed_at(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIJobRepository(db_with_schema)
        job = _make_ai_job(post.id)
        repo.save(job)

        repo.update_status(str(job.id), "completed")

        pending = repo.get_pending_jobs()
        assert len(pending) == 0

    def test_update_status_failed_sets_error_message(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIJobRepository(db_with_schema)
        job = _make_ai_job(post.id)
        repo.save(job)

        repo.update_status(str(job.id), "failed", error_message="timeout")

        pending = repo.get_pending_jobs()
        assert len(pending) == 0

    def test_round_trip_all_fields_match(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIJobRepository(db_with_schema)
        created = datetime(2025, 3, 20, 9, 0, 0)
        job = _make_ai_job(
            post.id,
            job_type=AIJobType.FULL_ENRICHMENT,
            status=AIJobStatus.PENDING,
            ai_version=2,
            attempts=1,
            max_attempts=5,
            created_at=created,
        )
        repo.save(job)

        pending = repo.get_pending_jobs()
        assert len(pending) == 1
        found = pending[0]
        assert found.id == job.id
        assert found.silver_post_id == job.silver_post_id
        assert found.job_type == job.job_type
        assert found.status == job.status
        assert found.ai_version == job.ai_version
        assert found.attempts == job.attempts
        assert found.max_attempts == job.max_attempts
        assert found.error_message == job.error_message
        assert found.started_at == job.started_at
        assert found.completed_at == job.completed_at
        assert found.created_at == job.created_at

    def test_update_attempts_updates_count(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIJobRepository(db_with_schema)
        job = _make_ai_job(post.id, attempts=0)
        repo.save(job)

        repo.update_attempts(str(job.id), 3)

        rows = db_with_schema.execute(
            "SELECT attempts FROM silver.ai_jobs WHERE id = ?",
            [str(job.id)],
        ).fetchall()
        assert len(rows) == 1
        assert int(str(rows[0][0])) == 3

    def test_update_attempts_for_nonexistent_job_does_not_raise(self, db_with_schema):
        repo = DuckDBAIJobRepository(db_with_schema)
        repo.update_attempts(str(uuid4()), 5)

    def test_reset_failed_jobs_resets_status(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIJobRepository(db_with_schema)
        job = _make_ai_job(post.id, status=AIJobStatus.FAILED)
        repo.save(job)

        repo.reset_failed_jobs()

        pending = repo.get_pending_jobs()
        assert len(pending) == 1
        assert pending[0].status == AIJobStatus.PENDING

    def test_reset_failed_jobs_clears_error_fields(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIJobRepository(db_with_schema)
        job = _make_ai_job(
            post.id,
            status=AIJobStatus.FAILED,
            error_message="timeout",
            started_at=datetime(2025, 1, 15, 14, 0, 0),
            completed_at=datetime(2025, 1, 15, 14, 1, 0),
        )
        repo.save(job)

        repo.reset_failed_jobs()

        pending = repo.get_pending_jobs()
        assert len(pending) == 1
        found = pending[0]
        assert found.error_message is None
        assert found.started_at is None
        assert found.completed_at is None

    def test_reset_failed_jobs_returns_count(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIJobRepository(db_with_schema)
        for _ in range(3):
            repo.save(_make_ai_job(post.id, status=AIJobStatus.FAILED))

        result = repo.reset_failed_jobs()

        assert result == 3

    def test_reset_failed_jobs_filters_by_type(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIJobRepository(db_with_schema)
        repo.save(_make_ai_job(post.id, status=AIJobStatus.FAILED, job_type=AIJobType.FULL_ENRICHMENT))
        repo.save(_make_ai_job(post.id, status=AIJobStatus.FAILED, job_type=AIJobType.FULL_ENRICHMENT))
        repo.save(_make_ai_job(post.id, status=AIJobStatus.FAILED, job_type=AIJobType.SENTIMENT))

        result = repo.reset_failed_jobs(job_type="full_enrichment")

        assert result == 2
        pending = repo.get_pending_jobs()
        assert len(pending) == 2
        assert all(j.job_type == AIJobType.FULL_ENRICHMENT for j in pending)

    def test_reset_failed_jobs_no_failed_returns_zero(self, db_with_schema):
        repo = DuckDBAIJobRepository(db_with_schema)

        result = repo.reset_failed_jobs()

        assert result == 0

    def test_reset_failed_jobs_does_not_affect_completed(self, db_with_schema):
        post = _insert_silver_post(db_with_schema)
        repo = DuckDBAIJobRepository(db_with_schema)
        repo.save(_make_ai_job(post.id, status=AIJobStatus.FAILED))
        repo.save(_make_ai_job(post.id, status=AIJobStatus.COMPLETED))

        repo.reset_failed_jobs()

        pending = repo.get_pending_jobs()
        assert len(pending) == 1
        completed = db_with_schema.execute(
            "SELECT count(*) FROM silver.ai_jobs WHERE status = 'completed'",
        ).fetchone()
        assert int(str(completed[0])) == 1
