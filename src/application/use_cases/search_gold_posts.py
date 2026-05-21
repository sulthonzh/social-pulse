from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.domain.interfaces import GoldPostSearchRepository


@dataclass(frozen=True)
class SearchGoldPostsResult:
    posts: list[dict[str, Any]]
    total: int


class SearchGoldPosts:
    def __init__(self, gold_repo: GoldPostSearchRepository) -> None:
        self._gold_repo = gold_repo

    def execute(
        self,
        keyword: str | None,
        sentiment: str | None,
        platform: str | None,
        start_date: object | None,
        end_date: object | None,
        offset: int,
        limit: int,
    ) -> SearchGoldPostsResult:
        posts, total = self._gold_repo.search_posts(
            keyword=keyword,
            sentiment=sentiment,
            platform=platform,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit,
        )
        return SearchGoldPostsResult(
            posts=[self._to_dict(p) for p in posts],
            total=total,
        )

    @staticmethod
    def _to_dict(post: Any) -> dict[str, Any]:
        return {
            "author": post.author_handle or post.author_name or "Unknown",
            "text": post.post_text or "",
            "sentiment": post.sentiment or "unknown",
            "confidence": round(float(post.sentiment_confidence or 0), 2),
            "date": str(post.posted_at)[:10] if post.posted_at else "",
            "likes": int(post.like_count or 0),
            "shares": int(post.share_count or 0),
            "replies": int(post.reply_count or 0),
            "platform": str(post.platform.value if hasattr(post.platform, "value") else post.platform or ""),
            "topic": str(post.topic_label or ""),
            "language": str(post.language or ""),
        }
