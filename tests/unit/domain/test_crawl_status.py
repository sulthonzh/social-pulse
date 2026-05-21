from __future__ import annotations

import pytest
from src.domain.value_objects.crawl_status import CrawlStatus


@pytest.mark.unit
class TestCrawlStatusEnumValues:
    def test_pending_exists(self) -> None:
        assert CrawlStatus.PENDING is not None

    def test_running_exists(self) -> None:
        assert CrawlStatus.RUNNING is not None

    def test_completed_exists(self) -> None:
        assert CrawlStatus.COMPLETED is not None

    def test_failed_exists(self) -> None:
        assert CrawlStatus.FAILED is not None

    def test_pending_string_value(self) -> None:
        assert CrawlStatus.PENDING.value == "pending"

    def test_running_string_value(self) -> None:
        assert CrawlStatus.RUNNING.value == "running"

    def test_completed_string_value(self) -> None:
        assert CrawlStatus.COMPLETED.value == "completed"

    def test_failed_string_value(self) -> None:
        assert CrawlStatus.FAILED.value == "failed"


@pytest.mark.unit
class TestCrawlStatusStrEnumBehavior:
    def test_status_is_string(self) -> None:
        assert isinstance(CrawlStatus.RUNNING, str)

    def test_value_lookup_running(self) -> None:
        assert CrawlStatus("running") is CrawlStatus.RUNNING

    def test_value_lookup_completed(self) -> None:
        assert CrawlStatus("completed") is CrawlStatus.COMPLETED

    def test_value_lookup_pending(self) -> None:
        assert CrawlStatus("pending") is CrawlStatus.PENDING

    def test_value_lookup_failed(self) -> None:
        assert CrawlStatus("failed") is CrawlStatus.FAILED
