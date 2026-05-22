from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.value_objects.platform import Platform
    from src.infrastructure.crawling.base import BaseCrawler


def create_crawler(platform: Platform | None = None) -> BaseCrawler:
    """Create appropriate crawler based on platform and configuration.

    Platform-aware factory:
    - youtube -> YouTubeCrawler (yt-dlp, no auth)
    - reddit  -> RedditCrawler (public JSON API, no auth)
    - twitter -> TwitterCrawler if bearer token set, else SimulationCrawler
    - None    -> SimulationCrawler (generic fallback)
    """
    if platform is not None:
        platform_value = platform.value if hasattr(platform, "value") else str(platform)

        if platform_value == "youtube":
            from src.infrastructure.crawling.youtube_crawler import YouTubeCrawler

            return YouTubeCrawler()

        if platform_value == "reddit":
            from src.infrastructure.crawling.reddit_crawler import RedditCrawler

            return RedditCrawler()

        if platform_value == "twitter":
            from src.shared.config import settings

            if settings.twitter_bearer_token:
                from src.infrastructure.crawling.twitter_crawler import TwitterCrawler

                return TwitterCrawler()

    from src.infrastructure.crawling.simulation_crawler import SimulationCrawler

    return SimulationCrawler()
