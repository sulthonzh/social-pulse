from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

import pytest
from src.domain.entities.search_request import SearchRequest
from src.domain.value_objects.crawl_status import CrawlStatus
from src.domain.value_objects.platform import Platform
from src.infrastructure.persistence.duckdb_search_request_repository import (
    DuckDBSearchRequestRepository,
)


def _make_search_request(**overrides) -> SearchRequest:
    return SearchRequest(
        id=overrides.get("id", uuid4()),
        keyword=overrides.get("keyword", "python"),
        start_date=overrides.get("start_date", date(2025, 1, 1)),
        end_date=overrides.get("end_date", date(2025, 1, 31)),
        platform=overrides.get("platform", Platform.TWITTER),
        status=overrides.get("status", CrawlStatus.PENDING),
        posts_found=overrides.get("posts_found", 0),
        created_at=overrides.get("created_at", datetime(2025, 1, 1, 0, 0, 0)),
        updated_at=overrides.get("updated_at", datetime(2025, 1, 1, 0, 0, 0)),
    )


@pytest.mark.unit
class TestDuckDBSearchRequestRepository:
    def test_save_returns_entity_with_id(self, db_with_schema):
        repo = DuckDBSearchRequestRepository(db_with_schema)
        sr = _make_search_request()
        result = repo.save(sr)
        assert result.id == sr.id
        assert result.keyword == sr.keyword

    def test_get_by_id_returns_saved_entity(self, db_with_schema):
        repo = DuckDBSearchRequestRepository(db_with_schema)
        sr = _make_search_request()
        repo.save(sr)

        found = repo.get_by_id(str(sr.id))
        assert found is not None
        assert found.id == sr.id

    def test_get_by_id_returns_none_for_nonexistent(self, db_with_schema):
        repo = DuckDBSearchRequestRepository(db_with_schema)
        assert repo.get_by_id(str(uuid4())) is None

    def test_get_by_keyword_returns_matching(self, db_with_schema):
        repo = DuckDBSearchRequestRepository(db_with_schema)
        sr = _make_search_request(keyword="python")
        repo.save(sr)

        results = repo.get_by_keyword("python")
        assert len(results) == 1
        assert results[0].keyword == "python"

    def test_get_by_keyword_returns_empty_for_nonmatching(self, db_with_schema):
        repo = DuckDBSearchRequestRepository(db_with_schema)
        sr = _make_search_request(keyword="python")
        repo.save(sr)

        results = repo.get_by_keyword("rust")
        assert results == []

    def test_update_status_updates_status_and_posts_found(self, db_with_schema):
        repo = DuckDBSearchRequestRepository(db_with_schema)
        sr = _make_search_request()
        repo.save(sr)

        repo.update_status(str(sr.id), "completed", 42)

        updated = repo.get_by_id(str(sr.id))
        assert updated is not None
        assert updated.status == CrawlStatus.COMPLETED
        assert updated.posts_found == 42

    def test_update_status_updates_updated_at(self, db_with_schema):
        repo = DuckDBSearchRequestRepository(db_with_schema)
        sr = _make_search_request()
        repo.save(sr)

        repo.update_status(str(sr.id), "running", 10)

        updated = repo.get_by_id(str(sr.id))
        assert updated is not None
        assert updated.updated_at > sr.updated_at

    def test_round_trip_all_fields_match(self, db_with_schema):
        repo = DuckDBSearchRequestRepository(db_with_schema)
        sr = _make_search_request()
        repo.save(sr)

        found = repo.get_by_id(str(sr.id))
        assert found is not None
        assert found.id == sr.id
        assert found.keyword == sr.keyword
        assert found.start_date == sr.start_date
        assert found.end_date == sr.end_date
        assert found.platform == sr.platform
        assert found.status == sr.status
        assert found.posts_found == sr.posts_found
        assert found.created_at == sr.created_at
        assert found.updated_at == sr.updated_at

    def test_get_by_keyword_multiple_same_keyword(self, db_with_schema):
        repo = DuckDBSearchRequestRepository(db_with_schema)
        sr1 = _make_search_request(
            keyword="python",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 15),
        )
        sr2 = _make_search_request(
            keyword="python",
            start_date=date(2025, 2, 1),
            end_date=date(2025, 2, 28),
        )
        repo.save(sr1)
        repo.save(sr2)

        results = repo.get_by_keyword("python")
        assert len(results) == 2
        ids = {r.id for r in results}
        assert sr1.id in ids
        assert sr2.id in ids
