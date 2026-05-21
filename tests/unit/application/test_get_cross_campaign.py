from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

import pytest
from src.application.use_cases.get_cross_campaign import (
    CrossCampaignComparison,
    GetCrossCampaign,
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
        "sentiment": "positive",
        "sentiment_confidence": 0.9,
        "like_count": 10,
        "share_count": 5,
        "reply_count": 2,
        "view_count": 100,
        "hashtags": ["python"],
        "topic_label": "technology",
        "posted_at": datetime(2025, 1, 15, 10, 0, 0),
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


def _seed_campaign_with_posts(db_with_schema, sr_id, keyword, n_posts=3):
    post_repo = DuckDBGoldPostSearchRepository(db_with_schema)
    posts = [
        _make_gold_post(
            search_request_id=sr_id,
            keyword=keyword,
            posted_at=datetime(2025, 1, 10 + i, 10, 0, 0),
        )
        for i in range(n_posts)
    ]
    post_repo.save_batch(posts)


def _seed_campaign_with_summary(db_with_schema, sr_id, keyword, **overrides):
    summary = _make_summary(search_request_id=sr_id, keyword=keyword, **overrides)
    summary_repo = DuckDBGoldCampaignSummaryRepository(db_with_schema)
    summary_repo.save(summary)


@pytest.mark.unit
class TestGetCrossCampaignComparison:
    def test_returns_empty_when_no_ids_provided(self, db_with_schema):
        uc = GetCrossCampaign(db_with_schema)
        result = uc.execute([])
        assert isinstance(result, CrossCampaignComparison)
        assert result.campaigns == []
        assert result.sentiment_comparison == []
        assert result.volume_comparison == []
        assert result.engagement_comparison == []

    def test_returns_empty_when_ids_not_found(self, db_with_schema):
        uc = GetCrossCampaign(db_with_schema)
        result = uc.execute([str(uuid4()), str(uuid4())])
        assert result.campaigns == []

    def test_compares_two_campaigns_via_summaries(self, db_with_schema):
        sr1 = uuid4()
        sr2 = uuid4()
        _seed_campaign_with_summary(
            db_with_schema,
            sr1,
            "python",
            positive_pct=60.0,
            negative_pct=20.0,
            neutral_pct=20.0,
            total_likes=1000,
            total_shares=300,
            total_replies=200,
            total_views=50000,
        )
        _seed_campaign_with_summary(
            db_with_schema,
            sr2,
            "java",
            positive_pct=40.0,
            negative_pct=40.0,
            neutral_pct=20.0,
            total_likes=500,
            total_shares=100,
            total_replies=50,
            total_views=20000,
        )

        uc = GetCrossCampaign(db_with_schema)
        result = uc.execute([str(sr1), str(sr2)])

        assert len(result.campaigns) == 2
        keywords = [c.keyword for c in result.campaigns]
        assert "python" in keywords
        assert "java" in keywords

    def test_builds_sentiment_comparison(self, db_with_schema):
        sr1 = uuid4()
        sr2 = uuid4()
        _seed_campaign_with_summary(
            db_with_schema,
            sr1,
            "python",
            positive_pct=60.0,
            negative_pct=20.0,
            neutral_pct=20.0,
        )
        _seed_campaign_with_summary(
            db_with_schema,
            sr2,
            "java",
            positive_pct=40.0,
            negative_pct=40.0,
            neutral_pct=20.0,
        )

        uc = GetCrossCampaign(db_with_schema)
        result = uc.execute([str(sr1), str(sr2)])

        assert len(result.sentiment_comparison) == 2
        sc_by_kw = {s["campaign"]: s for s in result.sentiment_comparison}
        assert sc_by_kw["python"]["positive"] == 60.0
        assert sc_by_kw["java"]["positive"] == 40.0

    def test_builds_engagement_comparison(self, db_with_schema):
        sr1 = uuid4()
        sr2 = uuid4()
        _seed_campaign_with_summary(
            db_with_schema,
            sr1,
            "python",
            total_likes=1000,
            total_shares=300,
            total_replies=200,
            total_views=50000,
        )
        _seed_campaign_with_summary(
            db_with_schema,
            sr2,
            "java",
            total_likes=500,
            total_shares=100,
            total_replies=50,
            total_views=20000,
        )

        uc = GetCrossCampaign(db_with_schema)
        result = uc.execute([str(sr1), str(sr2)])

        assert len(result.engagement_comparison) == 2
        ec_by_kw = {e["campaign"]: e for e in result.engagement_comparison}
        assert ec_by_kw["python"]["likes"] == 1000
        assert ec_by_kw["java"]["likes"] == 500

    def test_skips_not_found_campaigns(self, db_with_schema):
        sr1 = uuid4()
        _seed_campaign_with_summary(db_with_schema, sr1, "python")

        uc = GetCrossCampaign(db_with_schema)
        result = uc.execute([str(sr1), str(uuid4())])

        assert len(result.campaigns) == 1
        assert result.campaigns[0].keyword == "python"

    def test_compares_campaigns_from_posts_only(self, db_with_schema):
        sr1 = uuid4()
        sr2 = uuid4()
        _seed_campaign_with_posts(db_with_schema, sr1, "python", n_posts=3)
        _seed_campaign_with_posts(db_with_schema, sr2, "java", n_posts=2)

        uc = GetCrossCampaign(db_with_schema)
        result = uc.execute([str(sr1), str(sr2)])

        assert len(result.campaigns) == 2
        keywords = [c.keyword for c in result.campaigns]
        assert "python" in keywords
        assert "java" in keywords

    def test_volume_comparison_from_posts(self, db_with_schema):
        sr1 = uuid4()
        sr2 = uuid4()
        _seed_campaign_with_posts(db_with_schema, sr1, "python", n_posts=2)
        _seed_campaign_with_posts(db_with_schema, sr2, "java", n_posts=1)

        uc = GetCrossCampaign(db_with_schema)
        result = uc.execute([str(sr1), str(sr2)])

        assert len(result.volume_comparison) == 3
        campaigns_in_vol = {v["campaign"] for v in result.volume_comparison}
        assert "python" in campaigns_in_vol
        assert "java" in campaigns_in_vol

    def test_single_campaign_still_returns_comparison(self, db_with_schema):
        sr1 = uuid4()
        _seed_campaign_with_summary(db_with_schema, sr1, "python")

        uc = GetCrossCampaign(db_with_schema)
        result = uc.execute([str(sr1)])

        assert len(result.campaigns) == 1
        assert len(result.sentiment_comparison) == 1
        assert len(result.engagement_comparison) == 1
