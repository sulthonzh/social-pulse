from __future__ import annotations

from typing import Protocol
from datetime import date

# Import domain types (these will exist when domain layer is complete)
from src.domain.entities.search_request import SearchRequest
from src.domain.entities.crawl_run import CrawlRun
from src.domain.entities.raw_post import RawPost
from src.domain.value_objects.platform import Platform


class PostRepository(Protocol):
    """Repository for Bronze layer raw post persistence."""

    def save_posts(self, posts: list[RawPost]) -> int:
        """Save raw posts to bronze_posts table. Returns count saved."""
        ...

    def get_posts_by_search(self, search_request_id: str) -> list[RawPost]:
        """Get all raw posts for a given search request."""
        ...

    def get_posts_by_crawl_run(self, crawl_run_id: str) -> list[RawPost]:
        """Get all raw posts for a given crawl run."""
        ...

    def count_posts_by_search(self, search_request_id: str) -> int:
        """Count raw posts for a given search request."""
        ...


class SearchRequestRepository(Protocol):
    """Repository for search request persistence."""

    def save(self, request: SearchRequest) -> SearchRequest:
        """Create a new search request. Returns the saved entity with generated id."""
        ...

    def get_by_id(self, request_id: str) -> SearchRequest | None:
        """Get a search request by its ID."""
        ...

    def get_by_keyword(self, keyword: str) -> list[SearchRequest]:
        """Get all search requests for a keyword."""
        ...

    def update_status(self, request_id: str, status: str, posts_found: int) -> None:
        """Update search request status and posts count."""
        ...


class CrawlRunRepository(Protocol):
    """Repository for crawl run persistence."""

    def save(self, crawl_run: CrawlRun) -> CrawlRun:
        """Create a new crawl run. Returns the saved entity with generated id."""
        ...

    def get_by_id(self, crawl_run_id: str) -> CrawlRun | None:
        """Get a crawl run by its ID."""
        ...

    def get_by_search_request(self, search_request_id: str) -> list[CrawlRun]:
        """Get all crawl runs for a search request."""
        ...

    def update_status(
        self,
        crawl_run_id: str,
        status: str,
        posts_fetched: int,
        error_message: str | None,
    ) -> None:
        """Update crawl run status, posts count, and optional error."""
        ...


class Crawler(Protocol):
    """Async interface for social media platform crawling."""

    async def crawl(
        self,
        keyword: str,
        start_date: date,
        end_date: date,
        platform: Platform,
        max_results: int = 1000,
    ) -> list[RawPost]:
        """Crawl posts matching the keyword within the date range.

        Args:
            keyword: Search keyword/hashtag
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            platform: Target social media platform
            max_results: Maximum number of posts to fetch

        Returns:
            List of RawPost entities with populated raw_payload

        Raises:
            CrawlError: If the crawl fails after retries
        """
        ...

    async def health_check(self) -> bool:
        """Check if the crawler's API is reachable."""
        ...