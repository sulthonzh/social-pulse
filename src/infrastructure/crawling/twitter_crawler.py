from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from uuid import uuid4

import httpx

from src.domain.entities.raw_post import RawPost
from src.domain.exceptions import CrawlError
from src.domain.value_objects.platform import Platform
from src.infrastructure.crawling.base import BaseCrawler
from src.shared.config import settings

logger = logging.getLogger(__name__)

_TWITTER_API_MAX_PER_REQUEST = 100


class TwitterCrawler(BaseCrawler):
    """Twitter/X API v2 crawler using httpx async client."""

    def __init__(self) -> None:
        self._base_url = "https://api.twitter.com/2"
        self._bearer_token = settings.twitter_bearer_token
        self._timeout = settings.crawl_timeout_seconds
        self._max_results = settings.max_crawl_results

    async def crawl(
        self,
        keyword: str,
        start_date: date,
        end_date: date,
        platform: Platform,
        max_results: int = 1000,
    ) -> list[RawPost]:
        """Crawl tweets matching keyword within date range.

        Uses Twitter API v2 recent search endpoint.
        Returns list of RawPost entities with raw_payload populated.

        Raises:
            CrawlError: If the API request fails.
        """
        limit = min(max_results, self._max_results)
        posts: list[RawPost] = []

        async with httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._bearer_token}"},
            timeout=self._timeout,
        ) as client:
            params: dict[str, str | int] = {
                "query": f"{keyword} lang:en -is:retweet",
                "start_time": f"{start_date}T00:00:00Z",
                "end_time": f"{end_date}T23:59:59Z",
                "max_results": min(limit, _TWITTER_API_MAX_PER_REQUEST),
                "tweet.fields": (
                    "created_at,author_id,text,public_metrics,lang"
                ),
            }

            try:
                response = await client.get(
                    "/tweets/search/recent", params=params
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "Twitter API error: status=%s body=%s",
                    exc.response.status_code,
                    exc.response.text,
                )
                raise CrawlError(
                    f"Twitter API returned {exc.response.status_code}"
                ) from exc
            except httpx.RequestError as exc:
                logger.error("Twitter request failed: %s", exc)
                raise CrawlError(
                    f"Twitter request failed: {exc}"
                ) from exc

            data = response.json()
            tweets = data.get("data", [])

            for tweet in tweets:
                post = RawPost(
                    id=uuid4(),
                    search_request_id=uuid4(),
                    crawl_run_id=uuid4(),
                    platform=Platform.TWITTER,
                    platform_id=tweet.get("id"),
                    author_handle=tweet.get("author_id"),
                    raw_payload=tweet,
                    fetched_at=datetime.now(UTC),
                )
                posts.append(post)

                if len(posts) >= limit:
                    break

        logger.info(
            "Crawled %d tweets for keyword '%s'", len(posts), keyword
        )
        return posts

    async def health_check(self) -> bool:
        """Check if the Twitter API is reachable.

        Returns True if the API responds (200 or 401).
        401 indicates the API is up but authentication is misconfigured.
        """
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._bearer_token}"
                },
                timeout=10,
            ) as client:
                response = await client.get(
                    "/tweets/search/recent",
                    params={"query": "test", "max_results": 1},
                )
                return response.status_code in (200, 401)
        except httpx.RequestError:
            logger.warning("Twitter health check failed")
            return False
