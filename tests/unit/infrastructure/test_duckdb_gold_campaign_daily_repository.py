from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from src.domain.entities.gold_campaign_daily import GoldCampaignDaily
from src.domain.value_objects.platform import Platform
from src.infrastructure.persistence.duckdb_gold_campaign_daily_repository import (
    DuckDBGoldCampaignDailyRepository,
)

if TYPE_CHECKING:
    import duckdb


def _make_daily(**overrides: object) -> GoldCampaignDaily:
    defaults: dict[str, object] = {
        "id": uuid4(),
        "search_request_id": uuid4(),
        "keyword": "python",
        "platform": Platform.TWITTER,
        "date": date(2025, 1, 15),
        "total_posts": 10,
        "positive_count": 5,
        "negative_count": 3,
        "neutral_count": 2,
        "avg_confidence": 0.88,
        "top_hashtags": ["python", "data"],
        "top_topics": ["technology"],
        "total_likes": 500,
        "total_shares": 200,
        "total_replies": 100,
        "total_views": 10000,
        "ai_version": 1,
        "created_at": datetime(2025, 1, 15, 12, 0, 0),
    }
    defaults.update(overrides)
    return GoldCampaignDaily.model_validate(defaults)


@pytest.mark.unit
class TestDuckDBGoldCampaignDailyRepository:

    def test_save_batch_returns_correct_count(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldCampaignDailyRepository(db_with_schema)
        records = [_make_daily() for _ in range(3)]
        inserted = repo.save_batch(records)
        assert inserted == 3

    def test_save_batch_empty_returns_zero(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldCampaignDailyRepository(db_with_schema)
        assert repo.save_batch([]) == 0

    def test_save_batch_duplicate_returns_zero(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldCampaignDailyRepository(db_with_schema)
        record = _make_daily()
        assert repo.save_batch([record]) == 1
        assert repo.save_batch([record]) == 0

    def test_get_by_search_request_returns_matching(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldCampaignDailyRepository(db_with_schema)
        sr_id = uuid4()
        records = [
            _make_daily(search_request_id=sr_id, date=date(2025, 1, i))
            for i in range(1, 4)
        ]
        repo.save_batch(records)

        results = repo.get_by_search_request(str(sr_id))
        assert len(results) == 3

    def test_get_by_search_request_ordered_by_date_asc(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldCampaignDailyRepository(db_with_schema)
        sr_id = uuid4()
        records = [
            _make_daily(search_request_id=sr_id, date=date(2025, 1, 20)),
            _make_daily(search_request_id=sr_id, date=date(2025, 1, 10)),
        ]
        repo.save_batch(records)

        results = repo.get_by_search_request(str(sr_id))
        assert len(results) == 2
        assert results[0].date == date(2025, 1, 10)
        assert results[1].date == date(2025, 1, 20)

    def test_get_by_search_request_returns_empty_for_nonexistent(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldCampaignDailyRepository(db_with_schema)
        assert repo.get_by_search_request(str(uuid4())) == []

    def test_get_volume_trend(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldCampaignDailyRepository(db_with_schema)
        records = [
            _make_daily(keyword="python", date=date(2025, 1, 1), total_posts=5),
            _make_daily(keyword="python", date=date(2025, 1, 2), total_posts=10),
        ]
        repo.save_batch(records)

        trend = repo.get_volume_trend("python")
        assert len(trend) == 2
        assert trend[0]["total_posts"] == 5
        assert trend[1]["total_posts"] == 10

    def test_round_trip_all_fields_match(self, db_with_schema: duckdb.DuckDBPyConnection):
        repo = DuckDBGoldCampaignDailyRepository(db_with_schema)
        record = _make_daily()
        repo.save_batch([record])

        results = repo.get_by_search_request(str(record.search_request_id))
        assert len(results) == 1
        found = results[0]
        assert found.id == record.id
        assert found.search_request_id == record.search_request_id
        assert found.keyword == record.keyword
        assert found.platform == record.platform
        assert found.date == record.date
        assert found.total_posts == record.total_posts
        assert found.positive_count == record.positive_count
        assert found.negative_count == record.negative_count
        assert found.neutral_count == record.neutral_count
        assert found.avg_confidence == pytest.approx(record.avg_confidence, abs=1e-6)
        assert found.top_hashtags == record.top_hashtags
        assert found.top_topics == record.top_topics
        assert found.total_likes == record.total_likes
        assert found.total_shares == record.total_shares
        assert found.total_replies == record.total_replies
        assert found.total_views == record.total_views
        assert found.ai_version == record.ai_version
        assert found.created_at == record.created_at
