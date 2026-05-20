from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from src.application.use_cases.build_campaign_summary import BuildCampaignSummary
from src.domain.entities.gold_post_search import GoldPostSearch
from src.domain.value_objects.platform import Platform


def _make_gold_post(**overrides) -> GoldPostSearch:
    defaults = {
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
    return GoldPostSearch(**defaults)


def _build_use_case():
    gold_post_search_repo = MagicMock(spec=["get_by_search_request"])
    gold_summary_repo = MagicMock(spec=["save"])
    use_case = BuildCampaignSummary(
        gold_post_search_repo=gold_post_search_repo,
        gold_summary_repo=gold_summary_repo,
    )
    return use_case, gold_post_search_repo, gold_summary_repo


@pytest.mark.unit
class TestBuildCampaignSummary:

    async def test_execute_builds_summary_from_posts(self):
        use_case, post_repo, summary_repo = _build_use_case()
        search_request_id = uuid4()
        posts = [
            _make_gold_post(search_request_id=search_request_id, sentiment="positive"),
            _make_gold_post(search_request_id=search_request_id, sentiment="negative", hashtags=["data"]),
            _make_gold_post(search_request_id=search_request_id, sentiment="neutral", platform=Platform.FACEBOOK),
        ]
        post_repo.get_by_search_request.return_value = posts
        summary_repo.save.side_effect = lambda summary: summary

        result = await use_case.execute(
            str(search_request_id),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        assert result.search_request_id == search_request_id
        assert result.keyword == "python"
        assert result.total_posts == 3
        assert result.positive_pct == 33.33
        assert result.negative_pct == 33.33
        assert result.neutral_pct == 33.33
        assert result.avg_confidence == 0.9
        assert result.total_engagement == 51
        assert result.total_likes == 30
        assert result.total_shares == 15
        assert result.total_replies == 6
        assert result.total_views == 300
        assert set(result.top_hashtags) == {"python", "data"}
        assert result.platforms == ["facebook", "twitter"]

    async def test_execute_handles_missing_confidence(self):
        use_case, post_repo, summary_repo = _build_use_case()
        search_request_id = uuid4()
        posts = [
            _make_gold_post(search_request_id=search_request_id, sentiment_confidence=None),
        ]
        post_repo.get_by_search_request.return_value = posts
        summary_repo.save.side_effect = lambda summary: summary

        result = await use_case.execute(
            str(search_request_id),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        assert result.avg_confidence is None

    async def test_execute_saves_empty_summary_when_no_posts(self):
        use_case, post_repo, summary_repo = _build_use_case()
        post_repo.get_by_search_request.return_value = []
        summary_repo.save.side_effect = lambda summary: summary

        result = await use_case.execute(
            str(uuid4()),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        assert result.total_posts == 0
        assert result.keyword == ""
        summary_repo.save.assert_called_once()
