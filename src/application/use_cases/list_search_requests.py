from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities.search_request import SearchRequest
    from src.domain.interfaces import SearchRequestRepository


class ListSearchRequests:
    def __init__(self, repo: SearchRequestRepository) -> None:
        self._repo = repo

    def execute(self, limit: int = 20) -> list[SearchRequest]:
        return self._repo.get_recent(limit)
