"""YouTube crawler using yt-dlp — no API key required.

Searches YouTube videos by keyword and extracts metadata including
title, description, channel info, view/like counts, and upload date.
Uses yt-dlp's Python API with async-to-sync bridging via asyncio.to_thread.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from src.domain.entities.raw_post import RawPost
from src.domain.exceptions import CrawlError
from src.domain.value_objects.platform import Platform
from src.infrastructure.crawling.base import BaseCrawler

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _extract_metadata(info: dict[str, Any]) -> dict[str, Any]:
    """Extract standardized metadata from a yt-dlp video info dict."""
    return {
        "id": info.get("id", ""),
        "title": info.get("title", ""),
        "description": info.get("description", ""),
        "channel": info.get("channel", ""),
        "channel_id": info.get("channel_id", ""),
        "uploader": info.get("uploader", ""),
        "upload_date": info.get("upload_date", ""),
        "duration": info.get("duration"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "comment_count": info.get("comment_count"),
        "tags": info.get("tags", []),
        "categories": info.get("categories", []),
        "thumbnail": info.get("thumbnail", ""),
        "url": info.get("webpage_url", info.get("original_url", "")),
    }


def _parse_upload_date(upload_date_str: str) -> date | None:
    """Parse yt-dlp upload_date string (YYYYMMDD) to date."""
    if not upload_date_str or len(upload_date_str) != 8:
        return None
    try:
        return date(
            int(upload_date_str[:4]),
            int(upload_date_str[4:6]),
            int(upload_date_str[6:8]),
        )
    except (ValueError, IndexError):
        return None


class YouTubeCrawler(BaseCrawler):
    """YouTube crawler using yt-dlp — zero authentication required.

    Uses yt-dlp's search extraction to find videos by keyword.
    Runs yt-dlp sync operations in a thread pool to avoid blocking the event loop.
    """

    def __init__(self) -> None:
        self._ydl_opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
        }

    async def crawl(
        self,
        keyword: str,
        start_date: date,
        end_date: date,
        platform: Platform,
        max_results: int = 1000,
    ) -> list[RawPost]:
        """Search YouTube videos by keyword within date range.

        Uses yt-dlp's `ytsearchN:` query prefix to fetch video results,
        then filters by upload date.
        """
        limit = min(max_results, 200)  # YouTube search returns ~200 max per query

        try:
            results = await asyncio.to_thread(self._search, keyword, limit)
        except Exception as exc:
            logger.error("YouTube search failed: %s", exc)
            raise CrawlError(f"YouTube search failed: {exc}") from exc

        posts: list[RawPost] = []
        for entry in results:
            upload_date = _parse_upload_date(entry.get("upload_date", ""))
            if upload_date is None:
                continue
            if upload_date < start_date or upload_date > end_date:
                continue

            metadata = _extract_metadata(entry)
            post_id = metadata["id"] or str(uuid4())

            posts.append(
                RawPost(
                    search_request_id=uuid4(),
                    crawl_run_id=uuid4(),
                    platform=Platform.YOUTUBE,
                    platform_id=post_id,
                    author_handle=metadata.get("channel") or metadata.get("uploader"),
                    raw_payload=metadata,
                    fetched_at=datetime.now(UTC),
                )
            )

            if len(posts) >= max_results:
                break

        logger.info("YouTube: found %d videos for '%s'", len(posts), keyword)
        return posts

    def _search(self, keyword: str, limit: int) -> list[dict[str, Any]]:
        """Synchronous yt-dlp search — runs in thread pool."""
        import yt_dlp  # type: ignore[import-untyped]

        search_query = f"ytsearch{limit}:{keyword}"

        with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)

        entries = info.get("entries", []) if info else []
        return [e for e in entries if e is not None and e.get("id")]

    async def health_check(self) -> bool:
        """Check if YouTube is reachable by running a minimal search."""
        try:
            await asyncio.to_thread(self._search, "test", 1)
            return True
        except Exception:
            logger.warning("YouTube health check failed")
            return False
