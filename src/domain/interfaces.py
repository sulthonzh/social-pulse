from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import date

    from src.domain.entities.ai_enrichment import AIEnrichment
    from src.domain.entities.ai_job import AIJob
    from src.domain.entities.crawl_run import CrawlRun
    from src.domain.entities.enriched_post import EnrichedPost
    from src.domain.entities.gold_campaign_daily import GoldCampaignDaily
    from src.domain.entities.gold_campaign_summary import GoldCampaignSummary
    from src.domain.entities.gold_post_search import GoldPostSearch
    from src.domain.entities.language_result import LanguageResult
    from src.domain.entities.raw_post import RawPost
    from src.domain.entities.search_request import SearchRequest
    from src.domain.entities.sentiment_result import SentimentResult
    from src.domain.entities.topic_result import TopicResult
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


class EnrichedPostRepository(Protocol):
    """Repository for Silver layer enriched post persistence."""

    def save(self, post: EnrichedPost) -> EnrichedPost: ...
    def save_batch(self, posts: list[EnrichedPost]) -> int: ...
    def get_by_bronze_post_id(self, bronze_post_id: str) -> EnrichedPost | None: ...
    def get_by_search(self, search_request_id: str) -> list[EnrichedPost]: ...
    def count_by_search(self, search_request_id: str) -> int: ...


class AIEnrichmentRepository(Protocol):
    """Repository for AI enrichment results."""

    def save(self, enrichment: AIEnrichment) -> AIEnrichment: ...
    def get_by_post(self, silver_post_id: str, ai_version: int = 1) -> AIEnrichment | None: ...
    def get_by_search(self, search_request_id: str, ai_version: int = 1) -> list[AIEnrichment]: ...
    def get_max_version(self, silver_post_id: str) -> int: ...
    def get_by_posts(self, silver_post_ids: list[str], ai_version: int = 1) -> dict[str, AIEnrichment]: ...


class AIJobRepository(Protocol):
    """Repository for AI processing job queue."""

    def save(self, job: AIJob) -> AIJob: ...
    def get_pending_jobs(self, job_type: str | None = None, limit: int = 100) -> list[AIJob]: ...
    def update_status(self, job_id: str, status: str, error_message: str | None = None) -> None: ...
    def update_attempts(self, job_id: str, attempts: int) -> None: ...


class SentimentAnalyzer(Protocol):
    """Async interface for sentiment analysis."""

    async def analyze(self, text: str) -> SentimentResult: ...


class TopicExtractor(Protocol):
    """Async interface for topic extraction."""

    async def extract(self, text: str) -> TopicResult: ...


class LanguageDetector(Protocol):
    """Async interface for language detection."""

    async def detect(self, text: str) -> LanguageResult: ...


class GoldPostSearchRepository(Protocol):
    def save_batch(self, posts: list[GoldPostSearch]) -> int: ...
    def get_by_keyword(
        self, keyword: str, limit: int = 100, offset: int = 0
    ) -> list[GoldPostSearch]: ...
    def count_by_keyword(self, keyword: str) -> int: ...
    def get_sentiment_breakdown(self, keyword: str) -> list[dict[str, object]]: ...
    def get_filtered(
        self,
        keyword: str,
        sentiment: str | None = None,
        platform: str | None = None,
        language: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GoldPostSearch]: ...
    def get_by_search_request(self, search_request_id: str) -> list[GoldPostSearch]: ...


class GoldCampaignDailyRepository(Protocol):
    def save_batch(self, records: list[GoldCampaignDaily]) -> int: ...
    def get_by_search_request(self, search_request_id: str) -> list[GoldCampaignDaily]: ...
    def get_volume_trend(self, keyword: str) -> list[dict[str, object]]: ...


class GoldCampaignSummaryRepository(Protocol):
    def save(self, summary: GoldCampaignSummary) -> GoldCampaignSummary: ...
    def get_by_search_request(self, search_request_id: str) -> GoldCampaignSummary | None: ...
    def get_all_summaries(self) -> list[GoldCampaignSummary]: ...
