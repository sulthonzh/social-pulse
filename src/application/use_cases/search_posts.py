from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import structlog

from src.domain.entities.search_request import SearchRequest
from src.domain.value_objects.platform import Platform

if TYPE_CHECKING:
    from src.domain.interfaces import SearchRequestRepository

logger = structlog.get_logger(__name__)


class SearchPosts:
    """Create and persist a new search request for a campaign crawl."""

    def __init__(self, search_request_repo: SearchRequestRepository) -> None:
        self._search_request_repo = search_request_repo

    async def execute(
        self,
        keyword: str,
        platform: Platform,
        start_date: date,
        end_date: date,
    ) -> SearchRequest:
        request = SearchRequest(
            keyword=keyword,
            start_date=start_date,
            end_date=end_date,
            platform=platform,
        )
        saved = self._search_request_repo.save(request)
        logger.info(
            "search_request_created",
            request_id=str(saved.id),
            keyword=keyword,
            platform=platform.value,
        )
        return saved
