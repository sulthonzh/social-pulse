from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.infrastructure.crawling.base import BaseCrawler


def create_crawler() -> BaseCrawler:
    """Create appropriate crawler based on configuration.

    Returns SimulationCrawler (free, no API keys) when no Twitter bearer token
    is configured. Falls back to TwitterCrawler when credentials are available.
    """
    from src.shared.config import settings  # noqa: PLC0415

    if settings.twitter_bearer_token:
        from src.infrastructure.crawling.twitter_crawler import TwitterCrawler  # noqa: PLC0415

        return TwitterCrawler()

    from src.infrastructure.crawling.simulation_crawler import SimulationCrawler  # noqa: PLC0415

    return SimulationCrawler()
