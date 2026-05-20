from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date

    from src.domain.entities.raw_post import RawPost
    from src.domain.value_objects.platform import Platform

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """Abstract base class for social media crawlers."""

    @abstractmethod
    async def crawl(
        self,
        keyword: str,
        start_date: date,
        end_date: date,
        platform: Platform,
        max_results: int = 1000,
    ) -> list[RawPost]:
        """Crawl posts matching the keyword within the date range."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the crawler's API is reachable."""
        ...
