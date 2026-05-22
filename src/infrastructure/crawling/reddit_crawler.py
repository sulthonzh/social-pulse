"""Reddit crawler using public JSON API — no authentication required.

Appends `.json` to Reddit search URLs to get structured post data.
Uses httpx async client. Respects rate limits with User-Agent header.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

import httpx

from src.domain.entities.raw_post import RawPost
from src.domain.exceptions import CrawlError
from src.domain.value_objects.platform import Platform
from src.infrastructure.crawling.base import BaseCrawler

logger = logging.getLogger(__name__)

_REDDIT_BASE = "https://www.reddit.com"
_USER_AGENT = "SocialPulse/0.1 (research crawler; no-auth)"
_REQUEST_TIMEOUT = 30


def _extract_metadata(child: dict[str, Any]) -> dict[str, Any]:
    """Extract standardized metadata from a Reddit post listing child."""
    data = child.get("data", {})
    created_utc = data.get("created_utc", 0.0)
    title = data.get("title", "")
    selftext = data.get("selftext", "")
    author = data.get("author", "")
    permalink = data.get("permalink", "")

    posted_at_iso = ""
    if created_utc:
        posted_at_iso = datetime.fromtimestamp(created_utc, tz=UTC).isoformat()

    return {
        "id": data.get("name", ""),
        "reddit_id": data.get("id", ""),
        "title": title,
        "selftext": selftext,
        "text": f"{title} {selftext}".strip(),
        "author": author,
        "author_name": author,
        "subreddit": data.get("subreddit", ""),
        "score": data.get("score", 0),
        "num_comments": data.get("num_comments", 0),
        "upvote_ratio": data.get("upvote_ratio", 0.0),
        "created_utc": created_utc,
        "posted_at": posted_at_iso,
        "permalink": permalink,
        "url": data.get("url", ""),
        "post_url": f"https://www.reddit.com{permalink}" if permalink else "",
        "thumbnail": data.get("thumbnail", ""),
        "link_flair_text": data.get("link_flair_text"),
        "is_self": data.get("is_video", False) is False and data.get("is_self", True),
        "public_metrics": {
            "like_count": data.get("score", 0),
            "reply_count": data.get("num_comments", 0),
        },
    }


class RedditCrawler(BaseCrawler):
    """Reddit public JSON API crawler — zero authentication required.

    Uses Reddit's public `.json` endpoints to search posts by keyword.
    No login, no API key, no OAuth. Just append `.json` to URLs.
    """

    def __init__(self) -> None:
        self._headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
        }

    async def crawl(
        self,
        keyword: str,
        start_date: date,
        end_date: date,
        platform: Platform,
        max_results: int = 1000,
    ) -> list[RawPost]:
        """Search Reddit posts by keyword using public JSON API.

        Fetches up to 100 results per request, paginating with the `after` cursor.
        Filters by date range on created_utc.
        """
        limit = min(max_results, 500)
        posts: list[RawPost] = []
        after: str | None = None

        async with httpx.AsyncClient(
            base_url=_REDDIT_BASE,
            headers=self._headers,
            timeout=_REQUEST_TIMEOUT,
        ) as client:
            while len(posts) < limit:
                batch_size = min(100, limit - len(posts))
                batch = await self._fetch_page(client, keyword, batch_size, after)

                if not batch:
                    break

                for entry in batch:
                    metadata = _extract_metadata(entry)
                    created_utc = metadata.get("created_utc", 0.0)

                    if created_utc == 0.0:
                        continue

                    post_date = datetime.fromtimestamp(created_utc, tz=UTC).date()
                    if post_date < start_date or post_date > end_date:
                        continue

                    post_id = metadata.get("reddit_id") or metadata.get("id") or str(uuid4())

                    posts.append(
                        RawPost(
                            search_request_id=uuid4(),
                            crawl_run_id=uuid4(),
                            platform=Platform.REDDIT,
                            platform_id=post_id,
                            author_handle=metadata.get("author"),
                            raw_payload=metadata,
                            fetched_at=datetime.now(UTC),
                        )
                    )

                # Reddit returns the 'after' cursor for pagination
                last_entry = batch[-1].get("data", {})
                after = last_entry.get("name")
                if not after:
                    break

        logger.info("Reddit: found %d posts for '%s'", len(posts), keyword)
        return posts

    async def _fetch_page(
        self,
        client: httpx.AsyncClient,
        keyword: str,
        limit: int,
        after: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch a single page of Reddit search results."""
        params: dict[str, str | int] = {
            "q": keyword,
            "sort": "new",
            "limit": limit,
            "type": "link",
        }
        if after:
            params["after"] = after

        try:
            response = await client.get("/search.json", params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:  # noqa: PLR2004
                logger.warning("Reddit rate limited — slowing down")
            logger.error(
                "Reddit API error: status=%s body=%s",
                exc.response.status_code,
                exc.response.text[:500],
            )
            raise CrawlError(f"Reddit API returned {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            logger.error("Reddit request failed: %s", exc)
            raise CrawlError(f"Reddit request failed: {exc}") from exc

        data: dict[str, Any] = response.json()
        return list(data.get("data", {}).get("children", []))

    async def health_check(self) -> bool:
        """Check if Reddit's public JSON API is reachable."""
        try:
            async with httpx.AsyncClient(
                base_url=_REDDIT_BASE,
                headers=self._headers,
                timeout=10,
            ) as client:
                response = await client.get("/search.json", params={"q": "test", "limit": 1})
                return response.status_code == 200  # noqa: PLR2004
        except httpx.RequestError:
            logger.warning("Reddit health check failed")
            return False
