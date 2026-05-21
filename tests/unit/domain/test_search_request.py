from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

import pytest
from src.domain.entities.search_request import SearchRequest
from src.domain.value_objects.crawl_status import CrawlStatus
from src.domain.value_objects.platform import Platform


@pytest.mark.unit
class TestSearchRequestDefaults:
    def test_status_defaults_to_pending(self) -> None:
        sr = SearchRequest(
            keyword="python", start_date=date(2024, 1, 1), end_date=date(2024, 1, 31)
        )
        assert sr.status == CrawlStatus.PENDING

    def test_platform_defaults_to_twitter(self) -> None:
        sr = SearchRequest(
            keyword="python", start_date=date(2024, 1, 1), end_date=date(2024, 1, 31)
        )
        assert sr.platform == Platform.TWITTER

    def test_posts_found_defaults_to_zero(self) -> None:
        sr = SearchRequest(
            keyword="python", start_date=date(2024, 1, 1), end_date=date(2024, 1, 31)
        )
        assert sr.posts_found == 0

    def test_id_auto_generated(self) -> None:
        sr = SearchRequest(
            keyword="python", start_date=date(2024, 1, 1), end_date=date(2024, 1, 31)
        )
        assert sr.id is not None
        assert isinstance(sr.id, UUID)
        # Verify it parses as a valid UUID (no exception = valid)
        UUID(str(sr.id))

    def test_created_at_auto_populated(self) -> None:
        sr = SearchRequest(
            keyword="python", start_date=date(2024, 1, 1), end_date=date(2024, 1, 31)
        )
        assert sr.created_at is not None
        assert isinstance(sr.created_at, datetime)

    def test_updated_at_auto_populated(self) -> None:
        sr = SearchRequest(
            keyword="python", start_date=date(2024, 1, 1), end_date=date(2024, 1, 31)
        )
        assert sr.updated_at is not None
        assert isinstance(sr.updated_at, datetime)


@pytest.mark.unit
class TestSearchRequestExplicitOverrides:
    def test_explicit_id_overrides_default(self) -> None:
        explicit_id = uuid4()
        sr = SearchRequest(
            id=explicit_id,
            keyword="python",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        assert sr.id == explicit_id

    def test_explicit_platform_overrides_default(self) -> None:
        sr = SearchRequest(
            keyword="python",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            platform=Platform.INSTAGRAM,
        )
        assert sr.platform == Platform.INSTAGRAM

    def test_explicit_status_overrides_default(self) -> None:
        sr = SearchRequest(
            keyword="python",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            status=CrawlStatus.COMPLETED,
        )
        assert sr.status == CrawlStatus.COMPLETED


@pytest.mark.unit
class TestSearchRequestKeywordValidation:
    def test_empty_keyword_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="keyword must be non-empty"):
            SearchRequest(keyword="", start_date=date(2024, 1, 1), end_date=date(2024, 1, 31))

    def test_whitespace_only_keyword_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="keyword must be non-empty"):
            SearchRequest(keyword="   ", start_date=date(2024, 1, 1), end_date=date(2024, 1, 31))

    def test_valid_keyword_accepted(self) -> None:
        sr = SearchRequest(
            keyword="python", start_date=date(2024, 1, 1), end_date=date(2024, 1, 31)
        )
        assert sr.keyword == "python"


@pytest.mark.unit
class TestSearchRequestDateRangeValidation:
    def test_end_date_before_start_date_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="end_date"):
            SearchRequest(keyword="python", start_date=date(2024, 2, 1), end_date=date(2024, 1, 1))

    def test_end_date_equals_start_date_is_valid(self) -> None:
        sr = SearchRequest(
            keyword="python", start_date=date(2024, 1, 15), end_date=date(2024, 1, 15)
        )
        assert sr.start_date == sr.end_date

    def test_end_date_after_start_date_is_valid(self) -> None:
        sr = SearchRequest(
            keyword="python", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31)
        )
        assert sr.end_date > sr.start_date
