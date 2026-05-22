from __future__ import annotations

import threading
import time
from enum import StrEnum, unique
from typing import TYPE_CHECKING, Any, TypeVar

import structlog

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

logger = structlog.get_logger()

T = TypeVar("T")


@unique
class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    pass


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_seconds: float = 60.0,
        name: str = "default",
    ) -> None:
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._name = name
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._last_failure_time: float = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._maybe_transition_from_open()
            return self._state

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def record_success(self) -> None:
        with self._lock:
            self._consecutive_failures = 0
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                logger.info("circuit_closed", name=self._name)

    def record_failure(self) -> None:
        with self._lock:
            self._consecutive_failures += 1
            self._last_failure_time = time.monotonic()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning("circuit_reopened", name=self._name)
            elif self._consecutive_failures >= self._failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "circuit_opened",
                    name=self._name,
                    failures=self._consecutive_failures,
                )

    async def call(
        self,
        fn: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        with self._lock:
            self._maybe_transition_from_open()
            if self._state == CircuitState.OPEN:
                logger.warning("circuit_rejecting", name=self._name)
                raise CircuitOpenError(f"Circuit '{self._name}' is open")
            if self._state == CircuitState.HALF_OPEN:
                pass

        try:
            result = await fn(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise

    def _maybe_transition_from_open(self) -> None:
        if (
            self._state == CircuitState.OPEN
            and time.monotonic() - self._last_failure_time >= self._cooldown_seconds
        ):
            self._state = CircuitState.HALF_OPEN
            logger.info("circuit_half_open", name=self._name)
