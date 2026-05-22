from __future__ import annotations

import time

import pytest
from src.shared.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState


class TestCircuitStartsClosed:
    def test_initial_state(self) -> None:
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_initial_is_open_false(self) -> None:
        cb = CircuitBreaker()
        assert cb.is_open is False


class TestCircuitOpensAfterFailures:
    def test_opens_after_threshold(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_opens_with_default_threshold(self) -> None:
        cb = CircuitBreaker()
        for _ in range(5):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN


class TestCircuitBlocksCallsWhenOpen:
    @pytest.mark.asyncio
    async def test_raises_circuit_open_error(self) -> None:
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        assert cb.is_open

        async def noop() -> str:
            return "should not reach"

        with pytest.raises(CircuitOpenError):
            await cb.call(noop)


class TestCircuitHalfOpenAfterCooldown:
    def test_transitions_to_half_open(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.05)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.1)
        assert cb.state == CircuitState.HALF_OPEN

    def test_is_open_false_in_half_open(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.05)
        cb.record_failure()
        time.sleep(0.1)
        assert cb.is_open is False
        assert cb.state == CircuitState.HALF_OPEN


class TestCircuitClosesOnHalfOpenSuccess:
    @pytest.mark.asyncio
    async def test_success_closes_circuit(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.05)
        cb.record_failure()
        time.sleep(0.1)
        assert cb.state == CircuitState.HALF_OPEN

        async def succeed() -> str:
            return "ok"

        result = await cb.call(succeed)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED


class TestCircuitReopensOnHalfOpenFailure:
    @pytest.mark.asyncio
    async def test_failure_reopens_circuit(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.05)
        cb.record_failure()
        time.sleep(0.1)
        assert cb.state == CircuitState.HALF_OPEN

        async def fail() -> str:
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await cb.call(fail)
        assert cb.state == CircuitState.OPEN


class TestConsecutiveSuccessResetsFailures:
    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()

        async def succeed() -> str:
            return "ok"

        await cb.call(succeed)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
