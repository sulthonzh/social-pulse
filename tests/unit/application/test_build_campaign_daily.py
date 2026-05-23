from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from src.application.use_cases.build_campaign_daily import BuildCampaignDaily
from src.domain.entities.gold_post_search import GoldPostSearch
from src.domain.value_objects.platform import Platform

if TYPE_CHECKING:
    from src.domain.entities.gold_campaign_daily import GoldCampaignDaily


def _make_gold_post(**overrides: object) -> GoldPostSearch:
    defaults: dict[str, object] = {
        "search_request_id": uuid4(),
        "keyword": "python",
        "platform": Platform.TWITTER,
        "posted_at": datetime(2025, 1, 15, 10, 0, 0),
        "sentiment": "positive",
        "sentiment_confidence": 0.9,
        "topic_label": "technology",
        "hashtags": ["python"],
        "like_count": 10,
        "share_count": 5,
        "reply_count": 2,
        "view_count": 100,
    }
    defaults.update(overrides)
    return GoldPostSearch.model_validate(defaults)


def _build_use_case() -> tuple[BuildCampaignDaily, MagicMock, MagicMock]:
    gold_post_search_repo = MagicMock(spec=["get_by_search_request"])
    gold_daily_repo = MagicMock(spec=["save_batch"])
    use_case = BuildCampaignDaily(
        gold_post_search_repo=gold_post_search_repo,
        gold_daily_repo=gold_daily_repo,
    )
    return use_case, gold_post_search_repo, gold_daily_repo


@pytest.mark.unit
class TestBuildCampaignDaily:
    async def test_execute_aggregates_posts_by_date_and_platform(self) -> None:
        use_case, post_repo, daily_repo = _build_use_case()
        search_request_id = uuid4()
        posts = [
            _make_gold_post(search_request_id=search_request_id, sentiment="positive"),
            _make_gold_post(
                search_request_id=search_request_id, sentiment="negative", hashtags=["data"]
            ),
            _make_gold_post(
                search_request_id=search_request_id,
                posted_at=datetime(2025, 1, 16, 10, 0, 0),
                sentiment="neutral",
            ),
        ]
        post_repo.get_by_search_request.return_value = posts
        daily_repo.save_batch.return_value = 2

        result = await use_case.execute(str(search_request_id))

        assert result == 2
        records: list[GoldCampaignDaily] = daily_repo.save_batch.call_args[0][0]
        assert len(records) == 2
        first_day = next(r for r in records if r.date.isoformat() == "2025-01-15")
        assert first_day.total_posts == 2
        assert first_day.positive_count == 1
        assert first_day.negative_count == 1
        assert first_day.neutral_count == 0
        assert first_day.total_likes == 20
        assert first_day.total_shares == 10
        assert first_day.total_replies == 4
        assert first_day.total_views == 200
        assert set(first_day.top_hashtags) == {"python", "data"}

    async def test_execute_skips_posts_without_posted_at(self) -> None:
        use_case, post_repo, daily_repo = _build_use_case()
        search_request_id = uuid4()
        posts = [
            _make_gold_post(search_request_id=search_request_id, posted_at=None),
            _make_gold_post(search_request_id=search_request_id),
        ]
        post_repo.get_by_search_request.return_value = posts
        daily_repo.save_batch.return_value = 1

        result = await use_case.execute(str(search_request_id))

        assert result == 1
        records: list[GoldCampaignDaily] = daily_repo.save_batch.call_args[0][0]
        assert len(records) == 1

    async def test_execute_returns_zero_when_no_posts(self) -> None:
        use_case, post_repo, daily_repo = _build_use_case()
        post_repo.get_by_search_request.return_value = []

        result = await use_case.execute(str(uuid4()))

        assert result == 0
        daily_repo.save_batch.assert_not_called()

    async def test_execute_passes_lineage_to_daily_records(self) -> None:
        use_case, post_repo, daily_repo = _build_use_case()
        search_request_id = uuid4()
        posts = [
            _make_gold_post(search_request_id=search_request_id, sentiment="positive"),
        ]
        post_repo.get_by_search_request.return_value = posts
        daily_repo.save_batch.return_value = 1

        await use_case.execute(
            str(search_request_id),
            source_crawl_run_id="crawl-xyz",
            enrichment_job_id="job-uvw",
        )

        records: list[GoldCampaignDaily] = daily_repo.save_batch.call_args[0][0]
        assert len(records) == 1
        assert records[0].source_crawl_run_id == "crawl-xyz"
        assert records[0].enrichment_job_id == "job-uvw"
        assert records[0].lineage_updated_at is not None
