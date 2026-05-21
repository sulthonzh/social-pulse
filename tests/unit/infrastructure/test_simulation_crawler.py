from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

import pytest
from src.domain.value_objects.platform import Platform
from src.infrastructure.crawling.simulation_crawler import SimulationCrawler

if TYPE_CHECKING:
    from src.domain.entities.raw_post import RawPost


def _payload(post: RawPost) -> dict[str, Any]:
    assert post.raw_payload is not None
    return post.raw_payload


@pytest.mark.unit
class TestSimulationCrawler:
    async def test_crawl_returns_raw_posts(self):
        crawler = SimulationCrawler()
        posts = await crawler.crawl(
            keyword="python",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            platform=Platform.TWITTER,
        )
        assert len(posts) > 0
        for post in posts:
            assert post.raw_payload is not None

    async def test_crawl_posts_contain_keyword_in_text(self):
        crawler = SimulationCrawler()
        posts = await crawler.crawl(
            keyword="docker",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            platform=Platform.TWITTER,
        )
        for post in posts:
            payload = _payload(post)
            text: str = payload["text"]
            assert "docker" in text.lower()

    async def test_crawl_respects_max_results(self):
        crawler = SimulationCrawler()
        posts = await crawler.crawl(
            keyword="kubernetes",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            platform=Platform.TWITTER,
            max_results=5,
        )
        assert len(posts) <= 5

    async def test_crawl_posts_have_valid_payload(self):
        crawler = SimulationCrawler()
        posts = await crawler.crawl(
            keyword="rust",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            platform=Platform.TWITTER,
        )
        required_keys = {
            "id", "text", "posted_at", "author_id",
            "author_name", "public_metrics", "lang",
            "hashtags", "mentions",
        }
        for post in posts:
            payload = _payload(post)
            assert required_keys.issubset(payload.keys())

    async def test_crawl_posts_have_engagement_metrics(self):
        crawler = SimulationCrawler()
        posts = await crawler.crawl(
            keyword="golang",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            platform=Platform.TWITTER,
        )
        for post in posts:
            payload = _payload(post)
            metrics: dict[str, Any] = payload["public_metrics"]
            assert metrics["like_count"] >= 0
            assert metrics["retweet_count"] >= 0
            assert metrics["reply_count"] >= 0
            assert metrics["impression_count"] >= 0

    async def test_crawl_posts_dates_within_range(self):
        crawler = SimulationCrawler()
        start = date(2025, 3, 1)
        end = date(2025, 3, 31)
        posts = await crawler.crawl(
            keyword="tensorflow",
            start_date=start,
            end_date=end,
            platform=Platform.TWITTER,
        )
        for post in posts:
            payload = _payload(post)
            posted_str: str = payload["posted_at"]
            posted = date.fromisoformat(posted_str[:10])
            assert start <= posted <= end

    async def test_crawl_posts_have_hashtags(self):
        crawler = SimulationCrawler()
        posts = await crawler.crawl(
            keyword="react",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            platform=Platform.TWITTER,
        )
        for post in posts:
            payload = _payload(post)
            hashtags: list[Any] = payload["hashtags"]
            assert isinstance(hashtags, list)
            assert len(hashtags) >= 1

    async def test_crawl_posts_have_mentions(self):
        crawler = SimulationCrawler()
        posts = await crawler.crawl(
            keyword="vue",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            platform=Platform.TWITTER,
        )
        for post in posts:
            payload = _payload(post)
            mentions: list[Any] = payload["mentions"]
            assert isinstance(mentions, list)
            assert len(mentions) >= 1

    async def test_health_check_returns_true(self):
        crawler = SimulationCrawler()
        assert await crawler.health_check() is True

    async def test_crawl_with_different_keywords_produces_different_posts(self):
        crawler = SimulationCrawler()
        posts_a = await crawler.crawl(
            keyword="django",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            platform=Platform.TWITTER,
        )
        posts_b = await crawler.crawl(
            keyword="flask",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            platform=Platform.TWITTER,
        )
        texts_a = " ".join(_payload(p)["text"] for p in posts_a).lower()
        texts_b = " ".join(_payload(p)["text"] for p in posts_b).lower()
        assert "django" in texts_a
        assert "flask" in texts_b

    async def test_crawl_supports_all_platforms(self):
        crawler = SimulationCrawler()
        for platform in Platform:
            posts = await crawler.crawl(
                keyword="test",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
                platform=platform,
            )
            assert len(posts) > 0
            for post in posts:
                assert post.platform == platform

    async def test_crawl_generates_realistic_author_handles(self):
        crawler = SimulationCrawler()
        posts = await crawler.crawl(
            keyword="scala",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            platform=Platform.TWITTER,
        )
        handles = {post.author_handle for post in posts}
        assert all(h is not None and h.startswith("@") for h in handles)
