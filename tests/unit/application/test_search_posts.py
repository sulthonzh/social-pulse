from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from src.application.use_cases.search_posts import SearchPosts
from src.domain.entities.search_request import SearchRequest
from src.domain.value_objects.platform import Platform


def _build_use_case():
    repo = MagicMock(spec=["save", "get_by_id", "get_by_keyword", "update_status"])
    return SearchPosts(search_request_repo=repo), repo


@pytest.mark.unit
class TestSearchPosts:
    async def test_creates_and_saves_search_request(self):
        use_case, repo = _build_use_case()
        expected = SearchRequest(
            keyword="python",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            platform=Platform.TWITTER,
        )
        repo.save.return_value = expected

        result = await use_case.execute(
            keyword="python",
            platform=Platform.TWITTER,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        assert result.keyword == "python"
        assert result.platform == Platform.TWITTER
        repo.save.assert_called_once()

        saved = repo.save.call_args[0][0]
        assert saved.keyword == "python"
        assert saved.start_date == date(2025, 1, 1)
        assert saved.end_date == date(2025, 1, 31)
        assert saved.platform == Platform.TWITTER

    async def test_facebook_platform(self):
        use_case, repo = _build_use_case()
        expected = SearchRequest(
            keyword="metaverse",
            start_date=date(2025, 3, 1),
            end_date=date(2025, 3, 31),
            platform=Platform.FACEBOOK,
        )
        repo.save.return_value = expected

        result = await use_case.execute(
            keyword="metaverse",
            platform=Platform.FACEBOOK,
            start_date=date(2025, 3, 1),
            end_date=date(2025, 3, 31),
        )

        assert result.platform == Platform.FACEBOOK

    async def test_instagram_platform(self):
        use_case, repo = _build_use_case()
        expected = SearchRequest(
            keyword="travel",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 30),
            platform=Platform.INSTAGRAM,
        )
        repo.save.return_value = expected

        result = await use_case.execute(
            keyword="travel",
            platform=Platform.INSTAGRAM,
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 30),
        )

        assert result.platform == Platform.INSTAGRAM

    async def test_returns_saved_entity(self):
        use_case, repo = _build_use_case()
        saved_id = uuid4()
        saved = SearchRequest(
            id=saved_id,
            keyword="ai",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            platform=Platform.TWITTER,
        )
        repo.save.return_value = saved

        result = await use_case.execute(
            keyword="ai",
            platform=Platform.TWITTER,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )

        assert result.id == saved_id

    async def test_raises_on_empty_keyword(self):
        use_case, repo = _build_use_case()
        with pytest.raises(ValueError, match="non-empty"):
            await use_case.execute(
                keyword="  ",
                platform=Platform.TWITTER,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
            )

    async def test_raises_on_invalid_date_range(self):
        use_case, repo = _build_use_case()
        with pytest.raises(ValueError, match="end_date"):
            await use_case.execute(
                keyword="test",
                platform=Platform.TWITTER,
                start_date=date(2025, 12, 1),
                end_date=date(2025, 1, 1),
            )
