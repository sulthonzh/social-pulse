from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from src.domain.entities.ai_enrichment import AIEnrichment
from src.domain.entities.ai_job import AIJob
from src.domain.entities.enriched_post import EnrichedPost
from src.domain.value_objects.ai_job_status import AIJobStatus
from src.domain.value_objects.ai_job_type import AIJobType
from src.domain.value_objects.platform import Platform
from src.domain.value_objects.sentiment_label import SentimentLabel
from src.infrastructure.persistence.duckdb_ai_enrichment_repository import (
    DuckDBAIEnrichmentRepository,
)
from src.infrastructure.persistence.duckdb_ai_job_repository import (
    DuckDBAIJobRepository,
)
from src.infrastructure.persistence.duckdb_enriched_post_repository import (
    DuckDBEnrichedPostRepository,
)


def _make_enriched_post(
    bronze_post_id: UUID | None = None,
    search_request_id: UUID | None = None,
    platform: Platform = Platform.TWITTER,
    author_handle: str = "test_user",
    post_text: str = "Test post content #test",
    like_count: int = 10,
    share_count: int = 5,
) -> EnrichedPost:
    return EnrichedPost(
        bronze_post_id=bronze_post_id or uuid4(),
        search_request_id=search_request_id or uuid4(),
        platform=platform,
        author_handle=author_handle,
        post_text=post_text,
        like_count=like_count,
        share_count=share_count,
    )


def _make_ai_enrichment(
    silver_post_id: UUID | None = None,
    ai_version: int = 1,
    sentiment: SentimentLabel = SentimentLabel.POSITIVE,
    sentiment_confidence: float = 0.95,
    topic_label: str = "testing",
    language: str = "en",
) -> AIEnrichment:
    return AIEnrichment(
        silver_post_id=silver_post_id or uuid4(),
        ai_version=ai_version,
        sentiment=sentiment,
        sentiment_confidence=sentiment_confidence,
        topic_label=topic_label,
        language=language,
    )


def _make_ai_job(
    silver_post_id: UUID | None = None,
    job_type: AIJobType = AIJobType.FULL_ENRICHMENT,
    status: AIJobStatus = AIJobStatus.PENDING,
    ai_version: int = 1,
) -> AIJob:
    return AIJob(
        silver_post_id=silver_post_id or uuid4(),
        job_type=job_type,
        status=status,
        ai_version=ai_version,
    )


def _seed_bronze_row(db_with_schema, table: str, row: dict) -> None:
    cols = ", ".join(row.keys())
    placeholders = ", ".join(["?"] * len(row))
    db_with_schema.execute(
        f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",  # noqa: S608
        list(row.values()),
    )


def _seed_bronze_post(db_with_schema, bronze_post_id: str | None = None) -> str:
    search_req_id = str(uuid4())
    crawl_run_id = str(uuid4())
    bp_id = bronze_post_id or str(uuid4())

    _seed_bronze_row(
        db_with_schema,
        "bronze.search_requests",
        {
            "id": search_req_id,
            "keyword": "test",
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "platform": "twitter",
            "status": "completed",
            "posts_found": 1,
        },
    )
    _seed_bronze_row(
        db_with_schema,
        "bronze.bronze_crawl_runs",
        {
            "id": crawl_run_id,
            "search_request_id": search_req_id,
            "platform": "twitter",
            "status": "completed",
            "posts_fetched": 1,
        },
    )
    _seed_bronze_row(
        db_with_schema,
        "bronze.bronze_posts",
        {
            "id": bp_id,
            "search_request_id": search_req_id,
            "crawl_run_id": crawl_run_id,
            "platform": "twitter",
            "platform_id": f"pid-{bp_id[:8]}",
            "author_handle": "bronze_user",
            "raw_payload": '{"text": "raw post"}',
        },
    )
    return bp_id


def _seed_silver_post(
    db_with_schema,
    bronze_post_id: str | None = None,
    search_request_id: str | None = None,
) -> EnrichedPost:
    bp_id = _seed_bronze_post(db_with_schema, bronze_post_id)
    if search_request_id is None:
        search_request_id = str(uuid4())
        _seed_bronze_row(
            db_with_schema,
            "bronze.search_requests",
            {
                "id": search_request_id,
                "keyword": "silver-seed",
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "platform": "twitter",
                "status": "completed",
                "posts_found": 0,
            },
        )

    repo = DuckDBEnrichedPostRepository(db_with_schema)
    post = _make_enriched_post(
        bronze_post_id=UUID(bp_id),
        search_request_id=UUID(search_request_id),
    )
    repo.save(post)
    return post


@pytest.mark.integration
class TestEnrichmentPipeline:

    def test_enriched_post_lifecycle(self, db_with_schema):
        bronze_post_id = _seed_bronze_post(db_with_schema)
        search_request_id = str(uuid4())

        _seed_bronze_row(
            db_with_schema,
            "bronze.search_requests",
            {
                "id": search_request_id,
                "keyword": "enrichment-test",
                "start_date": "2025-02-01",
                "end_date": "2025-02-28",
                "platform": "twitter",
                "status": "completed",
                "posts_found": 1,
            },
        )

        repo = DuckDBEnrichedPostRepository(db_with_schema)
        post = _make_enriched_post(
            bronze_post_id=UUID(bronze_post_id),
            search_request_id=UUID(search_request_id),
            author_handle="lifecycle_user",
            post_text="Integration test post",
            like_count=42,
            share_count=7,
        )
        repo.save(post)

        retrieved = repo.get_by_bronze_post_id(str(post.bronze_post_id))
        assert retrieved is not None
        assert retrieved.bronze_post_id == post.bronze_post_id
        assert retrieved.search_request_id == post.search_request_id
        assert retrieved.platform == Platform.TWITTER
        assert retrieved.author_handle == "lifecycle_user"
        assert retrieved.post_text == "Integration test post"
        assert retrieved.like_count == 42
        assert retrieved.share_count == 7
        assert retrieved.reply_count == 0
        assert retrieved.view_count == 0
        assert retrieved.is_retweet is False

    def test_enriched_post_search_filter(self, db_with_schema):
        search_id = str(uuid4())
        other_search_id = str(uuid4())

        for sid in (search_id, other_search_id):
            _seed_bronze_row(
                db_with_schema,
                "bronze.search_requests",
                {
                    "id": sid,
                    "keyword": f"search-{sid[:8]}",
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-31",
                    "platform": "twitter",
                    "status": "completed",
                    "posts_found": 0,
                },
            )

        repo = DuckDBEnrichedPostRepository(db_with_schema)

        target_sid = UUID(search_id)
        for i in range(3):
            bp_id = _seed_bronze_post(db_with_schema)
            post = _make_enriched_post(
                bronze_post_id=UUID(bp_id),
                search_request_id=target_sid,
                post_text=f"Target post {i}",
            )
            repo.save(post)

        other_sid = UUID(other_search_id)
        bp_id = _seed_bronze_post(db_with_schema)
        post = _make_enriched_post(
            bronze_post_id=UUID(bp_id),
            search_request_id=other_sid,
            post_text="Other post",
        )
        repo.save(post)

        results = repo.get_by_search(search_id)
        assert len(results) == 3
        assert all(r.search_request_id == target_sid for r in results)

        count = repo.count_by_search(search_id)
        assert count == 3

        other_results = repo.get_by_search(other_search_id)
        assert len(other_results) == 1

    def test_ai_enrichment_lifecycle(self, db_with_schema):
        silver_post = _seed_silver_post(db_with_schema)

        repo = DuckDBAIEnrichmentRepository(db_with_schema)
        enrichment = _make_ai_enrichment(
            silver_post_id=silver_post.id,
            sentiment=SentimentLabel.POSITIVE,
            sentiment_confidence=0.92,
            topic_label="machine-learning",
            language="en",
        )
        repo.save(enrichment)

        retrieved = repo.get_by_post(str(silver_post.id), ai_version=1)
        assert retrieved is not None
        assert retrieved.silver_post_id == silver_post.id
        assert retrieved.ai_version == 1
        assert retrieved.sentiment == SentimentLabel.POSITIVE
        assert retrieved.sentiment_confidence == pytest.approx(0.92, abs=0.01)
        assert retrieved.topic_label == "machine-learning"
        assert retrieved.language == "en"

    def test_ai_job_status_transitions(self, db_with_schema):
        silver_post = _seed_silver_post(db_with_schema)

        repo = DuckDBAIJobRepository(db_with_schema)

        job = _make_ai_job(
            silver_post_id=silver_post.id,
            job_type=AIJobType.SENTIMENT,
            status=AIJobStatus.RUNNING,
        )
        repo.save(job)

        row = db_with_schema.execute(
            "SELECT status, job_type FROM silver.ai_jobs WHERE id = ?",
            [str(job.id)],
        ).fetchone()
        assert row is not None
        assert row[0] == "running"
        assert row[1] == "sentiment"

        repo.update_status(str(job.id), "completed")
        row = db_with_schema.execute(
            "SELECT status, completed_at FROM silver.ai_jobs WHERE id = ?",
            [str(job.id)],
        ).fetchone()
        assert row is not None
        assert row[0] == "completed"
        assert row[1] is not None

        new_job = _make_ai_job(
            silver_post_id=silver_post.id,
            job_type=AIJobType.TOPIC,
            status=AIJobStatus.RUNNING,
        )
        repo.save(new_job)
        repo.update_status(str(new_job.id), "failed", error_message="Model timeout")

        row = db_with_schema.execute(
            "SELECT status, error_message FROM silver.ai_jobs WHERE id = ?",
            [str(new_job.id)],
        ).fetchone()
        assert row is not None
        assert row[0] == "failed"
        assert "Model timeout" in str(row[1])

    def test_ai_enrichment_versioning(self, db_with_schema):
        silver_post = _seed_silver_post(db_with_schema)

        repo = DuckDBAIEnrichmentRepository(db_with_schema)

        v1 = _make_ai_enrichment(
            silver_post_id=silver_post.id,
            ai_version=1,
            sentiment=SentimentLabel.POSITIVE,
            sentiment_confidence=0.85,
            topic_label="v1-topic",
        )
        repo.save(v1)

        v2 = _make_ai_enrichment(
            silver_post_id=silver_post.id,
            ai_version=2,
            sentiment=SentimentLabel.NEGATIVE,
            sentiment_confidence=0.91,
            topic_label="v2-topic",
        )
        repo.save(v2)

        retrieved_v1 = repo.get_by_post(str(silver_post.id), ai_version=1)
        assert retrieved_v1 is not None
        assert retrieved_v1.sentiment == SentimentLabel.POSITIVE
        assert retrieved_v1.topic_label == "v1-topic"

        retrieved_v2 = repo.get_by_post(str(silver_post.id), ai_version=2)
        assert retrieved_v2 is not None
        assert retrieved_v2.sentiment == SentimentLabel.NEGATIVE
        assert retrieved_v2.topic_label == "v2-topic"

        row = db_with_schema.execute(
            "SELECT count(*) FROM silver.silver_ai_enrichment"
            " WHERE silver_post_id = ?",
            [str(silver_post.id)],
        ).fetchone()
        assert row is not None
        assert row[0] == 2

    def test_full_enrichment_pipeline(self, db_with_schema):
        bronze_post_id = _seed_bronze_post(db_with_schema)
        search_request_id = str(uuid4())
        _seed_bronze_row(
            db_with_schema,
            "bronze.search_requests",
            {
                "id": search_request_id,
                "keyword": "full-pipeline",
                "start_date": "2025-03-01",
                "end_date": "2025-03-31",
                "platform": "twitter",
                "status": "completed",
                "posts_found": 1,
            },
        )

        enriched_repo = DuckDBEnrichedPostRepository(db_with_schema)
        enrichment_repo = DuckDBAIEnrichmentRepository(db_with_schema)
        job_repo = DuckDBAIJobRepository(db_with_schema)

        silver_post = _make_enriched_post(
            bronze_post_id=UUID(bronze_post_id),
            search_request_id=UUID(search_request_id),
            author_handle="pipeline_user",
            post_text="Full pipeline test post",
            like_count=100,
        )
        enriched_repo.save(silver_post)

        enrichment = _make_ai_enrichment(
            silver_post_id=silver_post.id,
            sentiment=SentimentLabel.NEUTRAL,
            sentiment_confidence=0.78,
            topic_label="integration-testing",
            language="en",
        )
        enrichment_repo.save(enrichment)

        job = _make_ai_job(
            silver_post_id=silver_post.id,
            job_type=AIJobType.FULL_ENRICHMENT,
            status=AIJobStatus.COMPLETED,
        )
        job_repo.save(job)

        retrieved_post = enriched_repo.get_by_bronze_post_id(bronze_post_id)
        assert retrieved_post is not None
        assert retrieved_post.id == silver_post.id
        assert retrieved_post.author_handle == "pipeline_user"
        assert retrieved_post.post_text == "Full pipeline test post"
        assert retrieved_post.like_count == 100

        retrieved_enrichment = enrichment_repo.get_by_post(
            str(silver_post.id), ai_version=1,
        )
        assert retrieved_enrichment is not None
        assert retrieved_enrichment.silver_post_id == silver_post.id
        assert retrieved_enrichment.sentiment == SentimentLabel.NEUTRAL
        assert retrieved_enrichment.topic_label == "integration-testing"

        job_row = db_with_schema.execute(
            "SELECT status, job_type FROM silver.ai_jobs WHERE silver_post_id = ?",
            [str(silver_post.id)],
        ).fetchone()
        assert job_row is not None
        assert job_row[0] == "completed"
        assert job_row[1] == "full_enrichment"

        enrichments_by_search = enrichment_repo.get_by_search(search_request_id)
        assert len(enrichments_by_search) == 1
        assert enrichments_by_search[0].silver_post_id == silver_post.id

        count = enriched_repo.count_by_search(search_request_id)
        assert count == 1
