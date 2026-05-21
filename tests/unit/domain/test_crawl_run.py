from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError
from src.domain.entities.crawl_run import CrawlRun
from src.domain.value_objects.crawl_status import CrawlStatus
from src.domain.value_objects.platform import Platform


@pytest.mark.unit
class TestCrawlRunDefaults:
    def _make_crawl_run(self, **overrides: object) -> CrawlRun:
        defaults: dict[str, object] = {
            "search_request_id": uuid4(),
            "platform": Platform.TWITTER,
        }
        defaults.update(overrides)
        return CrawlRun(**defaults)  # type: ignore[arg-type]

    def test_status_defaults_to_running(self) -> None:
        cr = self._make_crawl_run()
        assert cr.status == CrawlStatus.RUNNING

    def test_posts_fetched_defaults_to_zero(self) -> None:
        cr = self._make_crawl_run()
        assert cr.posts_fetched == 0

    def test_error_message_defaults_to_none(self) -> None:
        cr = self._make_crawl_run()
        assert cr.error_message is None

    def test_completed_at_defaults_to_none(self) -> None:
        cr = self._make_crawl_run()
        assert cr.completed_at is None

    def test_id_auto_generated(self) -> None:
        cr = self._make_crawl_run()
        assert cr.id is not None
        assert isinstance(cr.id, UUID)
        UUID(str(cr.id))

    def test_started_at_auto_populated(self) -> None:
        cr = self._make_crawl_run()
        assert cr.started_at is not None
        assert isinstance(cr.started_at, datetime)


@pytest.mark.unit
class TestCrawlRunExplicitValues:
    def _make_crawl_run(self, **overrides: object) -> CrawlRun:
        defaults: dict[str, object] = {
            "search_request_id": uuid4(),
            "platform": Platform.TWITTER,
        }
        defaults.update(overrides)
        return CrawlRun(**defaults)  # type: ignore[arg-type]

    def test_explicit_status_override(self) -> None:
        cr = self._make_crawl_run(status=CrawlStatus.FAILED)
        assert cr.status == CrawlStatus.FAILED

    def test_explicit_error_message(self) -> None:
        cr = self._make_crawl_run(error_message="timeout")
        assert cr.error_message == "timeout"

    def test_explicit_id_override(self) -> None:
        explicit_id = uuid4()
        cr = self._make_crawl_run(id=explicit_id)
        assert cr.id == explicit_id

    def test_explicit_search_request_id(self) -> None:
        sr_id = UUID("12345678-1234-5678-1234-567812345678")
        cr = self._make_crawl_run(search_request_id=sr_id)
        assert cr.search_request_id == sr_id

    def test_explicit_platform(self) -> None:
        cr = self._make_crawl_run(platform=Platform.FACEBOOK)
        assert cr.platform == Platform.FACEBOOK


@pytest.mark.unit
class TestCrawlRunRequiredFields:
    def test_search_request_id_is_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            CrawlRun(platform=Platform.TWITTER)  # type: ignore[call-arg]

    def test_platform_is_required(self) -> None:
        with pytest.raises(PydanticValidationError):
            CrawlRun(search_request_id=uuid4())  # type: ignore[call-arg]
