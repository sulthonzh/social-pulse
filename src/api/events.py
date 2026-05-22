"""Lightweight in-memory event bus for pipeline SSE streaming."""

from __future__ import annotations

import asyncio
import dataclasses
import enum
from typing import Any


class PipelineStage(enum.StrEnum):
    CRAWLING = "crawling"
    ENRICHING = "enriching"
    GOLD = "gold"
    COMPLETE = "complete"
    ERROR = "error"


@dataclasses.dataclass(frozen=True, slots=True)
class PipelineEvent:
    """A single progress event from the pipeline."""

    run_id: str
    stage: PipelineStage
    current: int
    total: int
    message: str
    data: dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "stage": self.stage.value,
            "current": self.current,
            "total": self.total,
            "message": self.message,
            **self.data,
        }


class EventBus:
    """Simple pub/sub event bus keyed by pipeline run_id.

    Each run gets its own asyncio.Queue.  Subscribers consume from the queue.
    When the pipeline finishes, a sentinel (None) is pushed to signal completion.
    """

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[PipelineEvent | None]] = {}

    def create_run(self, run_id: str) -> None:
        """Create a queue for a new pipeline run."""
        self._queues[run_id] = asyncio.Queue()

    def publish(self, event: PipelineEvent) -> None:
        """Publish an event to the run's queue."""
        queue = self._queues.get(event.run_id)
        if queue is not None:
            queue.put_nowait(event)

    def complete(self, run_id: str) -> None:
        """Signal that the pipeline run is done."""
        queue = self._queues.get(run_id)
        if queue is not None:
            queue.put_nowait(None)

    def has_run(self, run_id: str) -> bool:
        """Check whether a run exists in the bus."""
        return run_id in self._queues

    def subscribe(self, run_id: str) -> asyncio.Queue[PipelineEvent | None]:
        """Get the queue for a run (for SSE consumption)."""
        return self._queues.get(run_id, asyncio.Queue())

    def remove(self, run_id: str) -> None:
        """Clean up after SSE client disconnects."""
        self._queues.pop(run_id, None)


# Global singleton
event_bus = EventBus()
