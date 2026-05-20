from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

import pytest
from src.application.use_cases.build_campaign_daily import BuildCampaignDaily
from src.application.use_cases.build_campaign_summary import BuildCampaignSummary
from src.application.use_cases.build_post_search import BuildPostSearch
from src.domain.entities.ai_enrichment import AIEnrichment
from src.domain.entities.enriched_post import EnrichedPost
from src.domain.value_objects.platform import Platform
from src.domain.value_objects.sentiment_label import SentimentLabel
from src.infrastructure.persistence.duckdb_ai_enrichment_repository import (
    DuckDBAIEnrichmentRepository,
)
from src.infrastructure.persistence.duckdb_enriched_post_repository import (
    DuckDBEnrichedPostRepository,
)
from src.infrastructure.persistence.duckdb_gold_campaign_daily_repository import (
    DuckDBGoldCampaignDailyRepository,
)
from src.infrastructure.persistence.duckdb_gold_campaign_summary_repository import (
    DuckDBGoldCampaignSummaryRepository,
)
from src.infrastructure.persistence.duckdb_gold_post_search_repository import (
    DuckDBGoldPostSearchRepository,
)


def _make_enriched_post(search_request_id, posted_at, platform=Platform.TWITTER) -> EnrichedPost:
    return EnrichedPost(
        bronze_post_id=uuid4(),
        search_request_id=search_request_id,
        platform=platform,
        platform_id=f"post-{uuid4().hex[:8]}",
        author_handle="data_nerd",
        author_name="Data Nerd",
        post_text="I love data engineering",
        posted_at=posted_at,
        like_count=10,
        share_count=5,
        reply_count=2,
        view_count=100,
        post_url="https://x.com/data_nerd/status/123",
    )


def _make_ai_enrichment(post_id, sentiment, hashtags, topic="technology") -> AIEnrichment:
    return AIEnrichment(
        silver_post_id=post_id,
        hashtags=hashtags,
        mentions=["@friend"],
        language="en",
        topic_label=topic,
        sentiment=sentiment,
        sentiment_confidence=0.9,
    )


@pytest.mark.integration
async def test_gold_pipeline_materializes_daily_and_summary(db_with_schema):
    enriched_repo = DuckDBEnrichedPostRepository(db_with_schema)
    ai_repo = DuckDBAIEnrichmentRepository(db_with_schema)
    post_search_repo = DuckDBGoldPostSearchRepository(db_with_schema)
    daily_repo = DuckDBGoldCampaignDailyRepository(db_with_schema)
    summary_repo = DuckDBGoldCampaignSummaryRepository(db_with_schema)

    search_request_id = uuid4()
    posts = [
        _make_enriched_post(search_request_id, datetime(2025, 1, 15, 10, 0, 0)),
        _make_enriched_post(search_request_id, datetime(2025, 1, 15, 11, 0, 0)),
        _make_enriched_post(search_request_id, datetime(2025, 1, 16, 10, 0, 0), Platform.FACEBOOK),
    ]
    enriched_repo.save_batch(posts)
    ai_repo.save(_make_ai_enrichment(posts[0].id, SentimentLabel.POSITIVE, ["python", "data"]))
    ai_repo.save(_make_ai_enrichment(posts[1].id, SentimentLabel.NEGATIVE, ["python"]))
    ai_repo.save(_make_ai_enrichment(posts[2].id, SentimentLabel.NEUTRAL, ["data"], "business"))

    build_post_search = BuildPostSearch(enriched_repo, ai_repo, post_search_repo)
    build_daily = BuildCampaignDaily(post_search_repo, daily_repo)
    build_summary = BuildCampaignSummary(post_search_repo, summary_repo)

    materialized = await build_post_search.execute(str(search_request_id), keyword="python")
    daily_records = await build_daily.execute(str(search_request_id))
    summary = await build_summary.execute(
        str(search_request_id),
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
    )

    assert materialized == 3
    assert daily_records == 2
    assert summary.total_posts == 3
    assert summary.positive_pct == 33.33
    assert summary.negative_pct == 33.33
    assert summary.neutral_pct == 33.33
    assert summary.total_likes == 30
    assert summary.total_shares == 15
    assert summary.total_replies == 6
    assert summary.total_views == 300
    assert summary.platforms == ["facebook", "twitter"]

    search_results = post_search_repo.get_by_search_request(str(search_request_id))
    assert len(search_results) == 3
    assert {p.sentiment for p in search_results} == {"positive", "negative", "neutral"}

    daily_results = daily_repo.get_by_search_request(str(search_request_id))
    assert len(daily_results) == 2
    assert sum(r.total_posts for r in daily_results) == 3

    saved_summary = summary_repo.get_by_search_request(str(search_request_id))
    assert saved_summary is not None
    assert saved_summary.total_posts == 3
