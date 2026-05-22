from __future__ import annotations

import pytest
from src.api.events import EventBus, PipelineEvent, PipelineStage


class TestPipelineStage:
    """Tests for PipelineStage enum."""

    def test_values(self) -> None:
        assert PipelineStage.CRAWLING == "crawling"
        assert PipelineStage.ENRICHING == "enriching"
        assert PipelineStage.GOLD == "gold"
        assert PipelineStage.COMPLETE == "complete"
        assert PipelineStage.ERROR == "error"


class TestPipelineEvent:
    """Tests for PipelineEvent dataclass."""

    def test_to_dict_basic(self) -> None:
        event = PipelineEvent(
            run_id="test-123",
            stage=PipelineStage.CRAWLING,
            current=5,
            total=100,
            message="Crawling...",
        )
        result = event.to_dict()
        assert result["run_id"] == "test-123"
        assert result["stage"] == "crawling"
        assert result["current"] == 5
        assert result["total"] == 100
        assert result["message"] == "Crawling..."

    def test_to_dict_with_data(self) -> None:
        event = PipelineEvent(
            run_id="test-456",
            stage=PipelineStage.COMPLETE,
            current=0,
            total=0,
            message="Done!",
            data={"posts_crawled": 42, "search_request_id": "abc"},
        )
        result = event.to_dict()
        assert result["posts_crawled"] == 42
        assert result["search_request_id"] == "abc"

    def test_to_dict_default_empty_data(self) -> None:
        event = PipelineEvent(
            run_id="test-789",
            stage=PipelineStage.ERROR,
            current=0,
            total=0,
            message="Failed",
        )
        result = event.to_dict()
        assert "posts_crawled" not in result

    def test_frozen(self) -> None:
        event = PipelineEvent(
            run_id="test",
            stage=PipelineStage.CRAWLING,
            current=0,
            total=0,
            message="test",
        )
        with pytest.raises(AttributeError):
            event.run_id = "changed"  # type: ignore[misc]


class TestEventBus:
    """Tests for EventBus pub/sub."""

    def test_create_run(self) -> None:
        bus = EventBus()
        bus.create_run("run-1")
        assert bus.has_run("run-1")

    def test_has_run_missing(self) -> None:
        bus = EventBus()
        assert not bus.has_run("nonexistent")

    def test_publish_and_subscribe(self) -> None:
        bus = EventBus()
        bus.create_run("run-1")
        event = PipelineEvent(
            run_id="run-1",
            stage=PipelineStage.CRAWLING,
            current=1,
            total=10,
            message="test",
        )
        bus.publish(event)
        queue = bus.subscribe("run-1")
        result = queue.get_nowait()
        assert result is not None
        assert result.run_id == "run-1"
        assert result.current == 1

    def test_publish_to_nonexistent_run(self) -> None:
        """Publishing to a run that doesn't exist should not raise."""
        bus = EventBus()
        event = PipelineEvent(
            run_id="ghost",
            stage=PipelineStage.CRAWLING,
            current=0,
            total=0,
            message="test",
        )
        bus.publish(event)  # Should not raise

    def test_complete_sends_sentinel(self) -> None:
        bus = EventBus()
        bus.create_run("run-1")
        bus.complete("run-1")
        queue = bus.subscribe("run-1")
        result = queue.get_nowait()
        assert result is None

    def test_complete_nonexistent_run(self) -> None:
        """Completing a run that doesn't exist should not raise."""
        bus = EventBus()
        bus.complete("ghost")  # Should not raise

    def test_remove_cleans_up(self) -> None:
        bus = EventBus()
        bus.create_run("run-1")
        bus.remove("run-1")
        assert not bus.has_run("run-1")

    def test_remove_nonexistent(self) -> None:
        """Removing a nonexistent run should not raise."""
        bus = EventBus()
        bus.remove("ghost")  # Should not raise

    def test_subscribe_missing_returns_empty_queue(self) -> None:
        bus = EventBus()
        queue = bus.subscribe("nonexistent")
        assert queue.empty()
