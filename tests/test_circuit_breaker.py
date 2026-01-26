import asyncio
import time
import pytest
from grpc import StatusCode

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.interceptors.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    CircuitBreakerOpenError,
    CircuitBreakerInterceptor,
)


class TestCircuitBreakerState:
    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self, circuit_breaker):
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_can_execute_when_closed(self, circuit_breaker):
        assert await circuit_breaker.can_execute() is True

    @pytest.mark.asyncio
    async def test_transitions_to_open_after_failures(self, circuit_breaker):
        for _ in range(3):
            await circuit_breaker.record_failure(StatusCode.UNAVAILABLE)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_cannot_execute_when_open(self, circuit_breaker):
        for _ in range(3):
            await circuit_breaker.record_failure(StatusCode.UNAVAILABLE)

        assert await circuit_breaker.can_execute() is False

    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_timeout(self, circuit_breaker):
        for _ in range(3):
            await circuit_breaker.record_failure(StatusCode.UNAVAILABLE)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        await asyncio.sleep(1.1)

        assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_allows_limited_calls(self, circuit_breaker):
        for _ in range(3):
            await circuit_breaker.record_failure(StatusCode.UNAVAILABLE)

        await asyncio.sleep(1.1)

        assert await circuit_breaker.can_execute() is True
        assert await circuit_breaker.can_execute() is True
        assert await circuit_breaker.can_execute() is False

    @pytest.mark.asyncio
    async def test_transitions_to_closed_after_successes_in_half_open(self, circuit_breaker):
        for _ in range(3):
            await circuit_breaker.record_failure(StatusCode.UNAVAILABLE)

        await asyncio.sleep(1.1)

        await circuit_breaker.can_execute()
        await circuit_breaker.record_success()
        await circuit_breaker.can_execute()
        await circuit_breaker.record_success()

        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_transitions_back_to_open_on_failure_in_half_open(self, circuit_breaker):
        for _ in range(3):
            await circuit_breaker.record_failure(StatusCode.UNAVAILABLE)

        await asyncio.sleep(1.1)

        await circuit_breaker.can_execute()
        await circuit_breaker.record_failure(StatusCode.UNAVAILABLE)

        assert circuit_breaker.state == CircuitBreakerState.OPEN


class TestCircuitBreakerFailureCounting:
    @pytest.mark.asyncio
    async def test_counts_configured_failure_codes(self, circuit_breaker):
        await circuit_breaker.record_failure(StatusCode.UNAVAILABLE)
        assert circuit_breaker._failure_count == 1

        await circuit_breaker.record_failure(StatusCode.DEADLINE_EXCEEDED)
        assert circuit_breaker._failure_count == 2

    @pytest.mark.asyncio
    async def test_ignores_non_failure_codes(self, circuit_breaker):
        await circuit_breaker.record_failure(StatusCode.NOT_FOUND)
        assert circuit_breaker._failure_count == 0

        await circuit_breaker.record_failure(StatusCode.INVALID_ARGUMENT)
        assert circuit_breaker._failure_count == 0

    @pytest.mark.asyncio
    async def test_success_decrements_failure_count(self, circuit_breaker):
        await circuit_breaker.record_failure(StatusCode.UNAVAILABLE)
        await circuit_breaker.record_failure(StatusCode.UNAVAILABLE)
        assert circuit_breaker._failure_count == 2

        await circuit_breaker.record_success()
        assert circuit_breaker._failure_count == 1

    @pytest.mark.asyncio
    async def test_failure_count_does_not_go_negative(self, circuit_breaker):
        await circuit_breaker.record_success()
        await circuit_breaker.record_success()

        assert circuit_breaker._failure_count == 0


class TestCircuitBreakerMetrics:
    @pytest.mark.asyncio
    async def test_tracks_total_calls(self, circuit_breaker):
        await circuit_breaker.record_success()
        await circuit_breaker.record_failure(StatusCode.UNAVAILABLE)
        await circuit_breaker.record_success()

        metrics = circuit_breaker.get_metrics()
        assert metrics["total_calls"] == 3

    @pytest.mark.asyncio
    async def test_tracks_successes_and_failures(self, circuit_breaker):
        await circuit_breaker.record_success()
        await circuit_breaker.record_success()
        await circuit_breaker.record_failure(StatusCode.UNAVAILABLE)

        metrics = circuit_breaker.get_metrics()
        assert metrics["total_successes"] == 2
        assert metrics["total_failures"] == 1

    @pytest.mark.asyncio
    async def test_tracks_state_changes(self, circuit_breaker):
        for _ in range(3):
            await circuit_breaker.record_failure(StatusCode.UNAVAILABLE)

        metrics = circuit_breaker.get_metrics()
        assert metrics["state_changes"] == 1
        assert metrics["state"] == "open"


class TestCircuitBreakerReset:
    @pytest.mark.asyncio
    async def test_manual_reset_returns_to_closed(self, circuit_breaker):
        for _ in range(3):
            await circuit_breaker.record_failure(StatusCode.UNAVAILABLE)

        assert circuit_breaker.state == CircuitBreakerState.OPEN

        await circuit_breaker.reset()

        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker._failure_count == 0


class TestCircuitBreakerInterceptor:
    @pytest.mark.asyncio
    async def test_allows_call_when_closed(
        self, circuit_breaker, mock_call_details, mock_success_continuation
    ):
        interceptor = CircuitBreakerInterceptor(circuit_breaker)

        result = await interceptor.intercept_unary_unary(
            mock_success_continuation,
            mock_call_details,
            {},
        )

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_blocks_call_when_open(
        self, circuit_breaker, mock_call_details, mock_success_continuation
    ):
        for _ in range(3):
            await circuit_breaker.record_failure(StatusCode.UNAVAILABLE)

        interceptor = CircuitBreakerInterceptor(circuit_breaker)

        with pytest.raises(CircuitBreakerOpenError):
            await interceptor.intercept_unary_unary(
                mock_success_continuation,
                mock_call_details,
                {},
            )

    @pytest.mark.asyncio
    async def test_uses_fallback_when_open(
        self, circuit_breaker, mock_call_details, mock_success_continuation
    ):
        for _ in range(3):
            await circuit_breaker.record_failure(StatusCode.UNAVAILABLE)

        async def fallback(request):
            return {"status": "fallback"}

        interceptor = CircuitBreakerInterceptor(circuit_breaker, fallback=fallback)

        result = await interceptor.intercept_unary_unary(
            mock_success_continuation,
            mock_call_details,
            {},
        )

        assert result["status"] == "fallback"

    @pytest.mark.asyncio
    async def test_records_success_on_successful_call(
        self, circuit_breaker, mock_call_details, mock_success_continuation
    ):
        interceptor = CircuitBreakerInterceptor(circuit_breaker)

        await interceptor.intercept_unary_unary(
            mock_success_continuation,
            mock_call_details,
            {},
        )

        assert circuit_breaker._total_successes == 1

    @pytest.mark.asyncio
    async def test_records_failure_on_grpc_error(
        self, circuit_breaker, mock_call_details, mock_failure_continuation
    ):
        interceptor = CircuitBreakerInterceptor(circuit_breaker)
        continuation = mock_failure_continuation(StatusCode.UNAVAILABLE)

        with pytest.raises(Exception):
            await interceptor.intercept_unary_unary(
                continuation,
                mock_call_details,
                {},
            )

        assert circuit_breaker._failure_count == 1


class TestCircuitBreakerConfiguration:
    @pytest.mark.asyncio
    async def test_custom_failure_threshold(self):
        config = CircuitBreakerConfig(failure_threshold=5)
        cb = CircuitBreaker("test", config)

        for i in range(4):
            await cb.record_failure(StatusCode.UNAVAILABLE)
            assert cb.state == CircuitBreakerState.CLOSED

        await cb.record_failure(StatusCode.UNAVAILABLE)
        assert cb.state == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_custom_success_threshold(self):
        config = CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=3,
            reset_timeout=0.1,
        )
        cb = CircuitBreaker("test", config)

        await cb.record_failure(StatusCode.UNAVAILABLE)
        await asyncio.sleep(0.15)

        await cb.can_execute()
        await cb.record_success()
        assert cb.state == CircuitBreakerState.HALF_OPEN

        await cb.can_execute()
        await cb.record_success()
        assert cb.state == CircuitBreakerState.HALF_OPEN

        await cb.can_execute()
        await cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED
