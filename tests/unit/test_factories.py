from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

import pytest
from src.domain.value_objects.ai_job_status import AIJobStatus
from src.domain.value_objects.ai_job_type import AIJobType
from src.domain.value_objects.crawl_status import CrawlStatus
from src.domain.value_objects.platform import Platform

from tests.factories import (
    make_ai_job,
    make_crawl_run,
    make_enriched_post,
    make_gold_campaign_daily,
    make_gold_campaign_summary,
    make_gold_post_search,
    make_raw_post,
    make_search_request,
)


@pytest.mark.unit
class TestMakeRawPost:
    def test_defaults(self) -> None:
        post = make_raw_post()
        assert post.platform == Platform.TWITTER
        assert post.platform_id is None
        assert post.author_handle is None
        assert post.raw_payload is None
        assert isinstance(post.fetched_at, datetime)

    def test_overrides(self) -> None:
        explicit_id = uuid4()
        post = make_raw_post(id=explicit_id, platform_id="tw_123")
        assert post.id == explicit_id
        assert post.platform_id == "tw_123"


@pytest.mark.unit
class TestMakeSearchRequest:
    def test_defaults(self) -> None:
        sr = make_search_request()
        assert sr.keyword == "test"
        assert sr.start_date == date(2024, 1, 1)
        assert sr.end_date == date(2024, 1, 31)
        assert sr.platform == Platform.TWITTER
        assert sr.status == CrawlStatus.PENDING

    def test_overrides(self) -> None:
        sr = make_search_request(keyword="python", platform=Platform.REDDIT)
        assert sr.keyword == "python"
        assert sr.platform == Platform.REDDIT


@pytest.mark.unit
class TestMakeEnrichedPost:
    def test_defaults(self) -> None:
        post = make_enriched_post()
        assert post.platform == Platform.TWITTER
        assert post.like_count == 0
        assert post.is_retweet is False
        assert isinstance(post.created_at, datetime)

    def test_overrides(self) -> None:
        post = make_enriched_post(post_text="hello", like_count=42)
        assert post.post_text == "hello"
        assert post.like_count == 42


@pytest.mark.unit
class TestMakeCrawlRun:
    def test_defaults(self) -> None:
        run = make_crawl_run()
        assert run.platform == Platform.TWITTER
        assert run.status == CrawlStatus.RUNNING
        assert run.posts_fetched == 0
        assert isinstance(run.started_at, datetime)

    def test_overrides(self) -> None:
        run = make_crawl_run(status=CrawlStatus.COMPLETED, posts_fetched=10)
        assert run.status == CrawlStatus.COMPLETED
        assert run.posts_fetched == 10


@pytest.mark.unit
class TestMakeAIJob:
    def test_defaults(self) -> None:
        job = make_ai_job()
        assert job.job_type == AIJobType.FULL_ENRICHMENT
        assert job.status == AIJobStatus.PENDING
        assert job.ai_version == 1
        assert isinstance(job.created_at, datetime)

    def test_overrides(self) -> None:
        job = make_ai_job(job_type=AIJobType.SENTIMENT, status=AIJobStatus.COMPLETED)
        assert job.job_type == AIJobType.SENTIMENT
        assert job.status == AIJobStatus.COMPLETED


@pytest.mark.unit
class TestMakeGoldPostSearch:
    def test_defaults(self) -> None:
        gps = make_gold_post_search()
        assert gps.keyword == "test"
        assert gps.platform == Platform.TWITTER
        assert gps.like_count == 0
        assert gps.hashtags == []

    def test_overrides(self) -> None:
        gps = make_gold_post_search(keyword="python", sentiment="positive")
        assert gps.keyword == "python"
        assert gps.sentiment == "positive"


@pytest.mark.unit
class TestMakeGoldCampaignDaily:
    def test_defaults(self) -> None:
        gcd = make_gold_campaign_daily()
        assert gcd.keyword == "test"
        assert gcd.date == date(2024, 1, 15)
        assert gcd.total_posts == 0

    def test_overrides(self) -> None:
        gcd = make_gold_campaign_daily(total_posts=100, positive_count=60)
        assert gcd.total_posts == 100
        assert gcd.positive_count == 60


@pytest.mark.unit
class TestMakeGoldCampaignSummary:
    def test_defaults(self) -> None:
        gcs = make_gold_campaign_summary()
        assert gcs.keyword == "test"
        assert gcs.start_date == date(2024, 1, 1)
        assert gcs.end_date == date(2024, 1, 31)
        assert gcs.total_posts == 0

    def test_overrides(self) -> None:
        gcs = make_gold_campaign_summary(total_posts=500, avg_confidence=0.85)
        assert gcs.total_posts == 500
        assert gcs.avg_confidence == 0.85
