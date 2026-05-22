from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

import pytest
from src.application.use_cases.get_campaign_analytics import (
    CampaignAnalytics,
    GetCampaignAnalytics,
)
from src.domain.entities.gold_campaign_summary import GoldCampaignSummary
from src.domain.entities.gold_post_search import GoldPostSearch
from src.domain.value_objects.platform import Platform
from src.infrastructure.persistence.duckdb_gold_campaign_summary_repository import (
    DuckDBGoldCampaignSummaryRepository,
)
from src.infrastructure.persistence.duckdb_gold_post_search_repository import (
    DuckDBGoldPostSearchRepository,
)


def _make_gold_post(**overrides) -> GoldPostSearch:
    defaults = {
        "id": uuid4(),
        "search_request_id": uuid4(),
        "keyword": "python",
        "platform": Platform.TWITTER,
        "author_handle": "testuser",
        "author_name": "Test User",
        "post_text": "Hello world",
        "posted_at": datetime(2025, 1, 15, 10, 0, 0),
        "post_url": "https://twitter.com/test/status/123",
        "sentiment": "positive",
        "sentiment_confidence": 0.95,
        "topic_label": "technology",
        "language": "en",
        "hashtags": ["python", "data"],
        "mentions": ["@friend"],
        "like_count": 10,
        "share_count": 5,
        "reply_count": 3,
        "view_count": 100,
        "ai_version": 1,
        "created_at": datetime(2025, 1, 15, 12, 0, 0),
    }
    defaults.update(overrides)
    return GoldPostSearch(**defaults)


def _make_summary(**overrides) -> GoldCampaignSummary:
    defaults = {
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
        "platforms": ["twitter"],
        "ai_version": 1,
        "created_at": datetime(2025, 1, 31, 12, 0, 0),
    }
    defaults.update(overrides)
    return GoldCampaignSummary(**defaults)


def _seed_posts(db_with_schema, sr_id, posts):
    repo = DuckDBGoldPostSearchRepository(db_with_schema)
    repo.save_batch(posts)
    return repo


def _seed_summary(db_with_schema, summary):
    repo = DuckDBGoldCampaignSummaryRepository(db_with_schema)
    repo.save(summary)
    return repo


@pytest.mark.unit
class TestGetCampaignAnalyticsFromSummary:
    def test_returns_analytics_from_campaign_summary(self, db_with_schema):
        sr_id = uuid4()
        summary = _make_summary(
            search_request_id=sr_id,
            keyword="python",
            total_posts=100,
            positive_pct=60.0,
            negative_pct=20.0,
            neutral_pct=20.0,
        )
        _seed_summary(db_with_schema, summary)

        uc = GetCampaignAnalytics(db_with_schema)
        result = uc.execute(str(sr_id))

        assert result is not None
        assert isinstance(result, CampaignAnalytics)
        assert result.keyword == "python"
        assert result.total_posts == 100
        assert result.positive_pct == 60.0
        assert result.negative_pct == 20.0
        assert result.neutral_pct == 20.0

    def test_returns_engagement_from_summary(self, db_with_schema):
        sr_id = uuid4()
        summary = _make_summary(
            search_request_id=sr_id,
            total_likes=1000,
            total_shares=300,
            total_replies=200,
            total_views=50000,
        )
        _seed_summary(db_with_schema, summary)

        uc = GetCampaignAnalytics(db_with_schema)
        result = uc.execute(str(sr_id))

        assert result is not None
        assert result.total_likes == 1000
        assert result.total_shares == 300
        assert result.total_replies == 200
        assert result.total_views == 50000

    def test_returns_top_hashtags_from_summary(self, db_with_schema):
        sr_id = uuid4()
        summary = _make_summary(
            search_request_id=sr_id,
            top_hashtags=["python", "data"],
        )
        _seed_summary(db_with_schema, summary)

        uc = GetCampaignAnalytics(db_with_schema)
        result = uc.execute(str(sr_id))

        assert result is not None
        assert len(result.top_hashtags) == 2

    def test_summary_with_none_pct_defaults_to_zero(self, db_with_schema):
        sr_id = uuid4()
        summary = _make_summary(
            search_request_id=sr_id,
            positive_pct=None,
            negative_pct=None,
            neutral_pct=None,
            avg_confidence=None,
        )
        _seed_summary(db_with_schema, summary)

        uc = GetCampaignAnalytics(db_with_schema)
        result = uc.execute(str(sr_id))

        assert result is not None
        assert result.positive_pct == 0.0
        assert result.negative_pct == 0.0
        assert result.neutral_pct == 0.0
        assert result.avg_confidence == 0.0


@pytest.mark.unit
class TestGetCampaignAnalyticsFromPostSearch:
    def test_computes_analytics_from_posts_when_no_summary(self, db_with_schema):
        sr_id = uuid4()
        posts = [
            _make_gold_post(
                search_request_id=sr_id,
                keyword="python",
                platform=Platform.TWITTER,
                sentiment="positive",
                sentiment_confidence=0.9,
                like_count=10,
                share_count=5,
                reply_count=2,
                view_count=100,
            ),
            _make_gold_post(
                search_request_id=sr_id,
                keyword="python",
                platform=Platform.TWITTER,
                sentiment="negative",
                sentiment_confidence=0.8,
                like_count=5,
                share_count=1,
                reply_count=0,
                view_count=50,
            ),
        ]
        _seed_posts(db_with_schema, sr_id, posts)

        uc = GetCampaignAnalytics(db_with_schema)
        result = uc.execute(str(sr_id))

        assert result is not None
        assert result.total_posts == 2
        assert result.positive_pct == 50.0
        assert result.negative_pct == 50.0
        assert result.neutral_pct == 0.0
        assert result.total_likes == 15
        assert result.total_shares == 6
        assert result.total_replies == 2
        assert result.total_views == 150

    def test_computes_sentiment_distribution(self, db_with_schema):
        sr_id = uuid4()
        posts = [
            _make_gold_post(search_request_id=sr_id, sentiment="positive"),
            _make_gold_post(search_request_id=sr_id, sentiment="positive"),
            _make_gold_post(search_request_id=sr_id, sentiment="negative"),
        ]
        _seed_posts(db_with_schema, sr_id, posts)

        uc = GetCampaignAnalytics(db_with_schema)
        result = uc.execute(str(sr_id))

        assert result is not None
        dist = {d["sentiment"]: d["count"] for d in result.sentiment_distribution}
        assert dist["positive"] == 2
        assert dist["negative"] == 1

    def test_computes_daily_volume(self, db_with_schema):
        sr_id = uuid4()
        posts = [
            _make_gold_post(
                search_request_id=sr_id,
                posted_at=datetime(2025, 1, 10, 10, 0, 0),
            ),
            _make_gold_post(
                search_request_id=sr_id,
                posted_at=datetime(2025, 1, 10, 14, 0, 0),
            ),
            _make_gold_post(
                search_request_id=sr_id,
                posted_at=datetime(2025, 1, 11, 10, 0, 0),
            ),
        ]
        _seed_posts(db_with_schema, sr_id, posts)

        uc = GetCampaignAnalytics(db_with_schema)
        result = uc.execute(str(sr_id))

        assert result is not None
        assert len(result.daily_volume) == 2
        day_counts = {v["date"]: v["count"] for v in result.daily_volume}
        assert day_counts["2025-01-10"] == 2
        assert day_counts["2025-01-11"] == 1

    def test_returns_none_for_nonexistent_request(self, db_with_schema):
        uc = GetCampaignAnalytics(db_with_schema)
        result = uc.execute(str(uuid4()))
        assert result is None

    def test_computes_avg_confidence_from_posts(self, db_with_schema):
        sr_id = uuid4()
        posts = [
            _make_gold_post(search_request_id=sr_id, sentiment_confidence=0.9),
            _make_gold_post(search_request_id=sr_id, sentiment_confidence=0.7),
        ]
        _seed_posts(db_with_schema, sr_id, posts)

        uc = GetCampaignAnalytics(db_with_schema)
        result = uc.execute(str(sr_id))

        assert result is not None
        assert result.avg_confidence == 0.8

    def test_computes_top_hashtags_from_posts(self, db_with_schema):
        sr_id = uuid4()
        posts = [
            _make_gold_post(search_request_id=sr_id, hashtags=["python", "data"]),
            _make_gold_post(search_request_id=sr_id, hashtags=["python", "ai"]),
            _make_gold_post(search_request_id=sr_id, hashtags=["python"]),
        ]
        _seed_posts(db_with_schema, sr_id, posts)

        uc = GetCampaignAnalytics(db_with_schema)
        result = uc.execute(str(sr_id))

        assert result is not None
        assert len(result.top_hashtags) > 0
        top_tag = result.top_hashtags[0]
        assert top_tag["hashtag"] == "python"

    def test_computes_top_topics_from_posts(self, db_with_schema):
        sr_id = uuid4()
        posts = [
            _make_gold_post(search_request_id=sr_id, topic_label="technology"),
            _make_gold_post(search_request_id=sr_id, topic_label="technology"),
            _make_gold_post(search_request_id=sr_id, topic_label="science"),
        ]
        _seed_posts(db_with_schema, sr_id, posts)

        uc = GetCampaignAnalytics(db_with_schema)
        result = uc.execute(str(sr_id))

        assert result is not None
        assert len(result.top_topics) > 0
        top_topic = result.top_topics[0]
        assert top_topic["topic"] == "technology"


@pytest.mark.unit
class TestGetCampaignAnalyticsSentimentDistributionFromSummary:
    def test_includes_sentiment_distribution_when_summary_exists(self, db_with_schema):
        sr_id = uuid4()
        summary = _make_summary(search_request_id=sr_id, keyword="python")
        _seed_summary(db_with_schema, summary)

        posts = [
            _make_gold_post(search_request_id=sr_id, keyword="python", sentiment="positive"),
            _make_gold_post(search_request_id=sr_id, keyword="python", sentiment="negative"),
        ]
        _seed_posts(db_with_schema, sr_id, posts)

        uc = GetCampaignAnalytics(db_with_schema)
        result = uc.execute(str(sr_id))

        assert result is not None
        assert len(result.sentiment_distribution) == 2
