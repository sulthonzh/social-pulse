from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.domain.entities.crawl_run import CrawlRun
from src.domain.entities.search_request import SearchRequest
from src.domain.value_objects.crawl_status import CrawlStatus
from src.domain.value_objects.platform import Platform
from src.infrastructure.persistence.duckdb_crawl_run_repository import (
    DuckDBCrawlRunRepository,
)
from src.infrastructure.persistence.duckdb_search_request_repository import (
    DuckDBSearchRequestRepository,
)


def _make_search_request() -> SearchRequest:
    return SearchRequest(
        id=uuid4(),
        keyword="python",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
        platform=Platform.TWITTER,
        status=CrawlStatus.PENDING,
        posts_found=0,
        created_at=datetime(2025, 1, 1, 0, 0, 0),
        updated_at=datetime(2025, 1, 1, 0, 0, 0),
    )


def _make_crawl_run(search_request_id, **overrides) -> CrawlRun:
    return CrawlRun(
        id=overrides.get("id", uuid4()),
        search_request_id=search_request_id,
        platform=overrides.get("platform", Platform.TWITTER),
        status=overrides.get("status", CrawlStatus.RUNNING),
        posts_fetched=overrides.get("posts_fetched", 0),
        error_message=overrides.get("error_message", None),
        started_at=overrides.get("started_at", datetime(2025, 1, 1, 12, 0, 0)),
        completed_at=overrides.get("completed_at", None),
    )


def _insert_search_request(db_with_schema) -> SearchRequest:
    sr_repo = DuckDBSearchRequestRepository(db_with_schema)
    sr = _make_search_request()
    sr_repo.save(sr)
    return sr


@pytest.mark.unit
class TestDuckDBCrawlRunRepository:

    def test_save_returns_entity_with_id(self, db_with_schema):
        sr = _insert_search_request(db_with_schema)
        repo = DuckDBCrawlRunRepository(db_with_schema)
        cr = _make_crawl_run(sr.id)
        result = repo.save(cr)
        assert result.id == cr.id

    def test_get_by_id_returns_saved_entity(self, db_with_schema):
        sr = _insert_search_request(db_with_schema)
        repo = DuckDBCrawlRunRepository(db_with_schema)
        cr = _make_crawl_run(sr.id)
        repo.save(cr)

        found = repo.get_by_id(str(cr.id))
        assert found is not None
        assert found.id == cr.id

    def test_get_by_id_returns_none_for_nonexistent(self, db_with_schema):
        repo = DuckDBCrawlRunRepository(db_with_schema)
        assert repo.get_by_id(str(uuid4())) is None

    def test_get_by_search_request_returns_matching(self, db_with_schema):
        sr = _insert_search_request(db_with_schema)
        repo = DuckDBCrawlRunRepository(db_with_schema)
        cr1 = _make_crawl_run(sr.id)
        cr2 = _make_crawl_run(sr.id)
        repo.save(cr1)
        repo.save(cr2)

        results = repo.get_by_search_request(str(sr.id))
        assert len(results) == 2

    def test_get_by_search_request_returns_empty_for_nonexistent(
        self, db_with_schema
    ):
        repo = DuckDBCrawlRunRepository(db_with_schema)
        results = repo.get_by_search_request(str(uuid4()))
        assert results == []

    def test_get_by_search_request_ordered_by_started_at(self, db_with_schema):
        sr = _insert_search_request(db_with_schema)
        repo = DuckDBCrawlRunRepository(db_with_schema)

        base = datetime(2025, 1, 1, 12, 0, 0)
        cr_earlier = _make_crawl_run(sr.id, started_at=base)
        cr_later = _make_crawl_run(
            sr.id, started_at=base + timedelta(hours=3)
        )
        repo.save(cr_earlier)
        repo.save(cr_later)

        results = repo.get_by_search_request(str(sr.id))
        assert len(results) == 2
        assert results[0].id == cr_earlier.id
        assert results[1].id == cr_later.id

    def test_update_status_completed_sets_completed_at(self, db_with_schema):
        sr = _insert_search_request(db_with_schema)
        repo = DuckDBCrawlRunRepository(db_with_schema)
        cr = _make_crawl_run(sr.id)
        repo.save(cr)

        repo.update_status(str(cr.id), "completed", 10, None)

        updated = repo.get_by_id(str(cr.id))
        assert updated is not None
        assert updated.status == CrawlStatus.COMPLETED
        assert updated.posts_fetched == 10
        assert updated.completed_at is not None

    def test_update_status_failed_sets_completed_at_and_error(self, db_with_schema):
        sr = _insert_search_request(db_with_schema)
        repo = DuckDBCrawlRunRepository(db_with_schema)
        cr = _make_crawl_run(sr.id)
        repo.save(cr)

        repo.update_status(str(cr.id), "failed", 0, "connection timeout")

        updated = repo.get_by_id(str(cr.id))
        assert updated is not None
        assert updated.status == CrawlStatus.FAILED
        assert updated.completed_at is not None
        assert updated.error_message == "connection timeout"

    def test_update_status_running_does_not_set_completed_at(self, db_with_schema):
        sr = _insert_search_request(db_with_schema)
        repo = DuckDBCrawlRunRepository(db_with_schema)
        cr = _make_crawl_run(sr.id)
        repo.save(cr)

        repo.update_status(str(cr.id), "running", 5, None)

        updated = repo.get_by_id(str(cr.id))
        assert updated is not None
        assert updated.status == CrawlStatus.RUNNING
        assert updated.posts_fetched == 5
        assert updated.completed_at is None

    def test_round_trip_all_fields_match(self, db_with_schema):
        sr = _insert_search_request(db_with_schema)
        repo = DuckDBCrawlRunRepository(db_with_schema)
        started = datetime(2025, 3, 15, 8, 30, 0)
        completed = datetime(2025, 3, 15, 9, 0, 0)
        cr = _make_crawl_run(
            sr.id,
            status=CrawlStatus.COMPLETED,
            posts_fetched=25,
            error_message=None,
            started_at=started,
            completed_at=completed,
        )
        repo.save(cr)

        found = repo.get_by_id(str(cr.id))
        assert found is not None
        assert found.id == cr.id
        assert found.search_request_id == cr.search_request_id
        assert found.platform == cr.platform
        assert found.status == cr.status
        assert found.posts_fetched == cr.posts_fetched
        assert found.error_message == cr.error_message
        assert found.started_at == cr.started_at
        assert found.completed_at == cr.completed_at