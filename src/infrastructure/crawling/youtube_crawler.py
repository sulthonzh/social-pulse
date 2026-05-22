"""YouTube crawler using yt-dlp — no API key required.

Searches YouTube videos by keyword and extracts metadata including
title, description, channel info, view/like counts, and upload date.
Uses yt-dlp's Python API with async-to-sync bridging via asyncio.to_thread.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from src.domain.entities.raw_post import RawPost
from src.domain.exceptions import CrawlError
from src.domain.value_objects.platform import Platform
from src.infrastructure.crawling.base import BaseCrawler

logger = logging.getLogger(__name__)


def _extract_metadata(info: dict[str, Any]) -> dict[str, Any]:
    """Extract standardized metadata from a yt-dlp video info dict."""
    upload_date_str = info.get("upload_date", "")
    title = info.get("title", "")
    description = info.get("description", "") or ""
    channel = info.get("channel", "")
    uploader = info.get("uploader", "")
    webpage_url = info.get("webpage_url", info.get("original_url", ""))

    posted_at_iso = ""
    if upload_date_str and len(upload_date_str) == 8:  # noqa: PLR2004
        posted_at_iso = (
            f"{upload_date_str[:4]}-{upload_date_str[4:6]}-{upload_date_str[6:8]}T00:00:00+00:00"
        )

    return {
        "id": info.get("id", ""),
        "title": title,
        "description": description,
        "text": f"{title} {description}".strip(),
        "channel": channel,
        "channel_id": info.get("channel_id", ""),
        "uploader": uploader,
        "author_name": channel or uploader,
        "upload_date": upload_date_str,
        "posted_at": posted_at_iso,
        "duration": info.get("duration"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "comment_count": info.get("comment_count"),
        "tags": info.get("tags", []),
        "categories": info.get("categories", []),
        "thumbnail": info.get("thumbnail", ""),
        "url": webpage_url,
        "post_url": webpage_url,
        "public_metrics": {
            "like_count": info.get("like_count", 0) or 0,
            "view_count": info.get("view_count", 0) or 0,
            "reply_count": info.get("comment_count", 0) or 0,
        },
    }


def _parse_upload_date(upload_date_str: str) -> date | None:
    """Parse yt-dlp upload_date string (YYYYMMDD) to date."""
    if not upload_date_str or len(upload_date_str) != 8:  # noqa: PLR2004
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
        self._flat_opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
        }
        self._full_opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "ignoreerrors": True,
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
        """Synchronous yt-dlp search — two-phase for full metadata.

        Phase 1: Flat search to get video IDs (fast).
        Phase 2: Per-video extraction to get full metadata including upload_date.
        Flat mode omits upload_date, so we must extract each video individually.
        """
        import yt_dlp  # noqa: PLC0415

        search_query = f"ytsearch{limit}:{keyword}"
        with yt_dlp.YoutubeDL(self._flat_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)

        entries = info.get("entries", []) if info else []
        video_ids = [e["id"] for e in entries if e is not None and e.get("id")]

        if not video_ids:
            return []

        results: list[dict[str, Any]] = []
        with yt_dlp.YoutubeDL(self._full_opts) as ydl:
            for vid_id in video_ids:
                try:
                    video_info = ydl.extract_info(
                        f"https://www.youtube.com/watch?v={vid_id}",
                        download=False,
                    )
                    if video_info and video_info.get("id"):
                        results.append(video_info)
                except Exception:
                    logger.warning("YouTube: failed to extract video %s, skipping", vid_id)
                    continue

        logger.info(
            "YouTube: phase1=%d ids, phase2=%d extracted",
            len(video_ids),
            len(results),
        )
        return results

    async def health_check(self) -> bool:
        """Check if YouTube is reachable by running a minimal search."""
        try:
            await asyncio.to_thread(self._search, "test", 1)
            return True
        except Exception:
            logger.warning("YouTube health check failed")
            return False
