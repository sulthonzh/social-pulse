from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from src.domain.entities.gold_campaign_summary import GoldCampaignSummary
from src.infrastructure.persistence.duckdb_gold_campaign_summary_repository import (
    DuckDBGoldCampaignSummaryRepository,
)

if TYPE_CHECKING:
    import duckdb


def _make_summary(**overrides: object) -> GoldCampaignSummary:
    defaults: dict[str, object] = {
        "id": uuid4(),
        "search_request_id": uuid4(),
        "keyword": "python",
        "start_date": date(2025, 1, 1),
        "end_date": date(2025, 1, 31),
        "total_posts": 100,
        "positive_pct": 60.0,
        "negative_pct": 20.0,
        "neutral_pct": 20.0,
        "avg_confidence": 0.85,
        "total_engagement": 1500,
        "total_likes": 1000,
        "total_shares": 300,
        "total_replies": 200,
        "total_views": 50000,
        "top_hashtags": ["python", "data"],
        "top_topics": ["technology"],
        "platforms": ["twitter", "facebook"],
        "ai_version": 1,
        "created_at": datetime(2025, 1, 31, 12, 0, 0),
    }
    defaults.update(overrides)
    return GoldCampaignSummary.model_validate(defaults)


@pytest.mark.unit
class TestDuckDBGoldCampaignSummaryRepository:
    def test_save_returns_entity_with_id(self, db_with_schema: duckdb.DuckDBPyConnection) -> None:
        repo = DuckDBGoldCampaignSummaryRepository(db_with_schema)
        summary = _make_summary()
        result = repo.save(summary)
        assert result.id == summary.id

    def test_get_by_search_request_returns_saved_entity(
        self, db_with_schema: duckdb.DuckDBPyConnection
    ) -> None:
        repo = DuckDBGoldCampaignSummaryRepository(db_with_schema)
        summary = _make_summary()
        repo.save(summary)

        found = repo.get_by_search_request(str(summary.search_request_id))
        assert found is not None
        assert found.id == summary.id

    def test_get_by_search_request_returns_none_for_nonexistent(
        self, db_with_schema: duckdb.DuckDBPyConnection
    ) -> None:
        repo = DuckDBGoldCampaignSummaryRepository(db_with_schema)
        assert repo.get_by_search_request(str(uuid4())) is None

    def test_get_all_summaries_returns_all(self, db_with_schema: duckdb.DuckDBPyConnection) -> None:
        repo = DuckDBGoldCampaignSummaryRepository(db_with_schema)
        summaries = [_make_summary() for _ in range(3)]
        for s in summaries:
            repo.save(s)

        results = repo.get_all_summaries()
        assert len(results) == 3

    def test_save_upserts_on_same_search_request_id(
        self, db_with_schema: duckdb.DuckDBPyConnection
    ) -> None:
        repo = DuckDBGoldCampaignSummaryRepository(db_with_schema)
        sr_id = uuid4()
        original = _make_summary(search_request_id=sr_id, total_posts=50)
        repo.save(original)

        updated = _make_summary(search_request_id=sr_id, total_posts=100)
        repo.save(updated)

        found = repo.get_by_search_request(str(sr_id))
        assert found is not None
        assert found.total_posts == 100

        all_results = repo.get_all_summaries()
        sr_count = sum(1 for s in all_results if s.search_request_id == sr_id)
        assert sr_count == 1

    def test_round_trip_all_fields_match(self, db_with_schema: duckdb.DuckDBPyConnection) -> None:
        repo = DuckDBGoldCampaignSummaryRepository(db_with_schema)
        summary = _make_summary(
            source_crawl_run_id="crawl-abc",
            enrichment_job_id="job-def",
            lineage_updated_at=datetime(2025, 1, 31, 14, 0, 0),
        )
        repo.save(summary)

        found = repo.get_by_search_request(str(summary.search_request_id))
        assert found is not None
        assert found.id == summary.id
        assert found.search_request_id == summary.search_request_id
        assert found.keyword == summary.keyword
        assert found.start_date == summary.start_date
        assert found.end_date == summary.end_date
        assert found.total_posts == summary.total_posts
        assert found.positive_pct == summary.positive_pct
        assert found.negative_pct == summary.negative_pct
        assert found.neutral_pct == summary.neutral_pct
        assert found.avg_confidence is not None
        assert summary.avg_confidence is not None
        assert abs(found.avg_confidence - summary.avg_confidence) < 1e-6
        assert found.total_engagement == summary.total_engagement
        assert found.total_likes == summary.total_likes
        assert found.total_shares == summary.total_shares
        assert found.total_replies == summary.total_replies
        assert found.total_views == summary.total_views
        assert found.top_hashtags == summary.top_hashtags
        assert found.top_topics == summary.top_topics
        assert found.platforms == summary.platforms
        assert found.ai_version == summary.ai_version
        assert found.source_crawl_run_id == "crawl-abc"
        assert found.enrichment_job_id == "job-def"
        assert found.lineage_updated_at == datetime(2025, 1, 31, 14, 0, 0)
        assert found.created_at == summary.created_at
