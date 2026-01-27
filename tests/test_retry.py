import sys
from pathlib import Path

import pytest
from grpc import StatusCode

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.interceptors.retry import RetryInterceptor, RetryPolicy


class TestRetryPolicy:
    def test_default_policy_values(self):
        policy = RetryPolicy()

        assert policy.max_attempts == 4
        assert policy.initial_backoff == 1.0
        assert policy.max_backoff == 30.0
        assert policy.backoff_multiplier == 2.0
        assert policy.jitter == 0.2

    def test_custom_policy_values(self):
        policy = RetryPolicy(
            max_attempts=5,
            initial_backoff=0.5,
            max_backoff=10.0,
            backoff_multiplier=3.0,
            jitter=0.1,
        )

        assert policy.max_attempts == 5
        assert policy.initial_backoff == 0.5
        assert policy.max_backoff == 10.0
        assert policy.backoff_multiplier == 3.0
        assert policy.jitter == 0.1

    def test_retryable_status_codes(self):
        policy = RetryPolicy()

        assert StatusCode.UNAVAILABLE in policy.retryable_status_codes
        assert StatusCode.DEADLINE_EXCEEDED in policy.retryable_status_codes
        assert StatusCode.RESOURCE_EXHAUSTED in policy.retryable_status_codes
        assert StatusCode.ABORTED in policy.retryable_status_codes
        assert StatusCode.NOT_FOUND not in policy.retryable_status_codes


class TestRetryInterceptorBackoff:
    def test_backoff_calculation_without_jitter(self, retry_policy):
        interceptor = RetryInterceptor(retry_policy)

        backoff_0 = interceptor._calculate_backoff(0)
        backoff_1 = interceptor._calculate_backoff(1)
        backoff_2 = interceptor._calculate_backoff(2)

        assert backoff_0 == retry_policy.initial_backoff
        assert backoff_1 == retry_policy.initial_backoff * retry_policy.backoff_multiplier
        assert backoff_2 == retry_policy.initial_backoff * (retry_policy.backoff_multiplier**2)

    def test_backoff_respects_max_backoff(self):
        policy = RetryPolicy(
            initial_backoff=1.0,
            max_backoff=5.0,
            backoff_multiplier=10.0,
            jitter=0.0,
        )
        interceptor = RetryInterceptor(policy)

        backoff = interceptor._calculate_backoff(10)

        assert backoff == policy.max_backoff


class TestRetryInterceptorRetryLogic:
    @pytest.mark.asyncio
    async def test_no_retry_on_success(
        self, retry_interceptor, mock_call_details, mock_success_continuation
    ):
        result = await retry_interceptor.intercept_unary_unary(
            mock_success_continuation,
            mock_call_details,
            {},
        )

        assert result["status"] == "success"
        assert retry_interceptor._total_retries == 0

    @pytest.mark.asyncio
    async def test_retries_on_retryable_error(
        self, retry_interceptor, mock_call_details, mock_intermittent_continuation
    ):
        continuation = mock_intermittent_continuation([1, 2])

        result = await retry_interceptor.intercept_unary_unary(
            continuation,
            mock_call_details,
            {},
        )

        assert result["status"] == "success"
        assert result["call_number"] == 3
        assert retry_interceptor._total_retries == 2

    @pytest.mark.asyncio
    async def test_exhausts_retries_on_persistent_failure(
        self, mock_call_details, mock_failure_continuation, mock_grpc_error
    ):
        policy = RetryPolicy(max_attempts=3, initial_backoff=0.01, jitter=0.0)
        interceptor = RetryInterceptor(policy)
        continuation = mock_failure_continuation(StatusCode.UNAVAILABLE)

        with pytest.raises(Exception):
            await interceptor.intercept_unary_unary(
                continuation,
                mock_call_details,
                {},
            )

        assert interceptor._total_retries == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_error(
        self, retry_interceptor, mock_call_details, mock_failure_continuation
    ):
        continuation = mock_failure_continuation(StatusCode.NOT_FOUND)

        with pytest.raises(Exception):
            await retry_interceptor.intercept_unary_unary(
                continuation,
                mock_call_details,
                {},
            )

        assert retry_interceptor._total_retries == 0

    @pytest.mark.asyncio
    async def test_successful_retry_increments_counter(
        self, mock_call_details, mock_intermittent_continuation
    ):
        policy = RetryPolicy(max_attempts=3, initial_backoff=0.01, jitter=0.0)
        interceptor = RetryInterceptor(policy)
        continuation = mock_intermittent_continuation([1])

        await interceptor.intercept_unary_unary(
            continuation,
            mock_call_details,
            {},
        )

        assert interceptor._successful_retries == 1


class TestRetryInterceptorCallback:
    @pytest.mark.asyncio
    async def test_on_retry_callback_is_called(
        self, mock_call_details, mock_intermittent_continuation
    ):
        retry_calls = []

        def on_retry(attempt, error, backoff):
            retry_calls.append((attempt, error, backoff))

        policy = RetryPolicy(max_attempts=3, initial_backoff=0.01, jitter=0.0)
        interceptor = RetryInterceptor(policy, on_retry=on_retry)
        continuation = mock_intermittent_continuation([1, 2])

        await interceptor.intercept_unary_unary(
            continuation,
            mock_call_details,
            {},
        )

        assert len(retry_calls) == 2
        assert retry_calls[0][0] == 1
        assert retry_calls[1][0] == 2


class TestRetryInterceptorMetrics:
    @pytest.mark.asyncio
    async def test_get_metrics(self, mock_call_details, mock_intermittent_continuation):
        policy = RetryPolicy(max_attempts=3, initial_backoff=0.01, jitter=0.0)
        interceptor = RetryInterceptor(policy)
        continuation = mock_intermittent_continuation([1])

        await interceptor.intercept_unary_unary(
            continuation,
            mock_call_details,
            {},
        )

        metrics = interceptor.get_metrics()

        assert metrics["total_retries"] == 1
        assert metrics["successful_retries"] == 1
        assert metrics["policy"]["max_attempts"] == 3


class TestRetryInterceptorStatusCodes:
    @pytest.mark.asyncio
    async def test_retries_unavailable(self, mock_call_details, mock_intermittent_continuation):
        policy = RetryPolicy(max_attempts=3, initial_backoff=0.01, jitter=0.0)
        interceptor = RetryInterceptor(policy)
        continuation = mock_intermittent_continuation([1], StatusCode.UNAVAILABLE)

        result = await interceptor.intercept_unary_unary(
            continuation,
            mock_call_details,
            {},
        )

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_retries_deadline_exceeded(
        self, mock_call_details, mock_intermittent_continuation
    ):
        policy = RetryPolicy(max_attempts=3, initial_backoff=0.01, jitter=0.0)
        interceptor = RetryInterceptor(policy)
        continuation = mock_intermittent_continuation([1], StatusCode.DEADLINE_EXCEEDED)

        result = await interceptor.intercept_unary_unary(
            continuation,
            mock_call_details,
            {},
        )

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_retries_resource_exhausted(
        self, mock_call_details, mock_intermittent_continuation
    ):
        policy = RetryPolicy(max_attempts=3, initial_backoff=0.01, jitter=0.0)
        interceptor = RetryInterceptor(policy)
        continuation = mock_intermittent_continuation([1], StatusCode.RESOURCE_EXHAUSTED)

        result = await interceptor.intercept_unary_unary(
            continuation,
            mock_call_details,
            {},
        )

        assert result["status"] == "success"
