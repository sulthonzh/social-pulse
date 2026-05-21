from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.interfaces import GoldPostSearchRepository


class GetCampaigns:
    def __init__(self, gold_repo: GoldPostSearchRepository) -> None:
        self._gold_repo = gold_repo

    def execute(self) -> list[dict[str, str]]:
        return self._gold_repo.get_campaigns()
