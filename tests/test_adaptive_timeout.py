import asyncio
import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.interceptors.adaptive_timeout import (
    TimeoutConfig,
    TimeoutManager,
    AdaptiveTimeoutInterceptor,
)


class TestTimeoutConfig:
    def test_default_values(self):
        config = TimeoutConfig()

        assert config.default_timeout == 30.0
        assert config.min_timeout == 5.0
        assert config.max_timeout == 120.0
        assert config.adaptive_enabled is True
        assert config.percentile == 95.0
        assert config.history_size == 100

    def test_method_specific_timeouts(self):
        config = TimeoutConfig()

        assert config.method_timeouts["HealthCheck"] == 5.0
        assert config.method_timeouts["CreatePlan"] == 60.0
        assert config.method_timeouts["GenerateCode"] == 90.0


class TestTimeoutManager:
    @pytest.mark.asyncio
    async def test_returns_default_timeout_for_unknown_method(self, timeout_manager):
        timeout = await timeout_manager.get_timeout("UnknownMethod")

        assert timeout == timeout_manager.config.default_timeout

    @pytest.mark.asyncio
    async def test_returns_method_specific_timeout(self, timeout_manager):
        timeout = await timeout_manager.get_timeout("/service/HealthCheck")

        assert timeout == timeout_manager.config.method_timeouts["HealthCheck"]

    @pytest.mark.asyncio
    async def test_records_response_time(self, timeout_manager):
        await timeout_manager.record_response_time("TestMethod", 1.0)
        await timeout_manager.record_response_time("TestMethod", 2.0)

        assert len(timeout_manager._response_times["TestMethod"]) == 2

    @pytest.mark.asyncio
    async def test_adaptive_timeout_with_history(self, timeout_manager):
        for i in range(15):
            await timeout_manager.record_response_time("TestMethod", 1.0 + i * 0.1)

        timeout = await timeout_manager.get_timeout("TestMethod")

        assert timeout >= timeout_manager.config.min_timeout
        assert timeout <= timeout_manager.config.max_timeout

    @pytest.mark.asyncio
    async def test_history_size_limit(self, timeout_manager):
        for i in range(30):
            await timeout_manager.record_response_time("TestMethod", float(i))

        assert (
            len(timeout_manager._response_times["TestMethod"])
            == timeout_manager.config.history_size
        )

    @pytest.mark.asyncio
    async def test_returns_base_timeout_with_insufficient_history(self, timeout_manager):
        for i in range(5):
            await timeout_manager.record_response_time("TestMethod", 1.0)

        timeout = await timeout_manager.get_timeout("TestMethod")

        assert timeout == timeout_manager.config.default_timeout

    @pytest.mark.asyncio
    async def test_adaptive_timeout_disabled(self):
        config = TimeoutConfig(adaptive_enabled=False, default_timeout=10.0)
        manager = TimeoutManager(config)

        for i in range(20):
            await manager.record_response_time("TestMethod", 100.0)

        timeout = await manager.get_timeout("TestMethod")

        assert timeout == 10.0


class TestTimeoutManagerPercentile:
    @pytest.mark.asyncio
    async def test_percentile_calculation(self, timeout_manager):
        data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        p95 = timeout_manager._get_percentile(data, 95.0)

        assert p95 == 10.0

    @pytest.mark.asyncio
    async def test_percentile_empty_data(self, timeout_manager):
        p95 = timeout_manager._get_percentile([], 95.0)

        assert p95 == timeout_manager.config.default_timeout


class TestTimeoutManagerMethodExtraction:
    @pytest.mark.asyncio
    async def test_extracts_method_from_path(self, timeout_manager):
        method_name = timeout_manager._extract_method_name("/ai_agent.ClaudeService/CreatePlan")

        assert method_name == "CreatePlan"

    @pytest.mark.asyncio
    async def test_handles_simple_method_name(self, timeout_manager):
        method_name = timeout_manager._extract_method_name("CreatePlan")

        assert method_name == "CreatePlan"


class TestTimeoutManagerMetrics:
    @pytest.mark.asyncio
    async def test_get_metrics_empty(self, timeout_manager):
        metrics = timeout_manager.get_metrics()

        assert metrics == {}

    @pytest.mark.asyncio
    async def test_get_metrics_with_data(self, timeout_manager):
        await timeout_manager.record_response_time("MethodA", 1.0)
        await timeout_manager.record_response_time("MethodA", 2.0)
        await timeout_manager.record_response_time("MethodA", 3.0)

        metrics = timeout_manager.get_metrics()

        assert "MethodA" in metrics
        assert metrics["MethodA"]["count"] == 3
        assert metrics["MethodA"]["avg"] == 2.0
        assert metrics["MethodA"]["min"] == 1.0
        assert metrics["MethodA"]["max"] == 3.0


class TestAdaptiveTimeoutInterceptor:
    @pytest.mark.asyncio
    async def test_applies_timeout_to_call(
        self, timeout_manager, mock_call_details, mock_success_continuation
    ):
        interceptor = AdaptiveTimeoutInterceptor(timeout_manager)
        captured_details = None

        async def capturing_continuation(details, request):
            nonlocal captured_details
            captured_details = details
            return {"status": "success"}

        await interceptor.intercept_unary_unary(
            capturing_continuation,
            mock_call_details,
            {},
        )

        assert captured_details.timeout is not None

    @pytest.mark.asyncio
    async def test_records_response_time_on_success(
        self, mock_call_details, mock_success_continuation
    ):
        manager = TimeoutManager()
        interceptor = AdaptiveTimeoutInterceptor(manager)

        await interceptor.intercept_unary_unary(
            mock_success_continuation,
            mock_call_details,
            {},
        )

        method = mock_call_details.method
        assert len(manager._response_times.get(method, [])) == 1

    @pytest.mark.asyncio
    async def test_records_response_time_on_failure(
        self, mock_call_details, mock_failure_continuation
    ):
        manager = TimeoutManager()
        interceptor = AdaptiveTimeoutInterceptor(manager)
        continuation = mock_failure_continuation()

        with pytest.raises(Exception):
            await interceptor.intercept_unary_unary(
                continuation,
                mock_call_details,
                {},
            )

        method = mock_call_details.method
        assert len(manager._response_times.get(method, [])) == 1


class TestAdaptiveTimeoutBounds:
    @pytest.mark.asyncio
    async def test_timeout_respects_min_bound(self):
        config = TimeoutConfig(
            min_timeout=10.0,
            max_timeout=100.0,
            adaptive_enabled=True,
            adjustment_factor=0.1,
        )
        manager = TimeoutManager(config)

        for i in range(15):
            await manager.record_response_time("FastMethod", 0.1)

        timeout = await manager.get_timeout("FastMethod")

        assert timeout >= config.min_timeout

    @pytest.mark.asyncio
    async def test_timeout_respects_max_bound(self):
        config = TimeoutConfig(
            min_timeout=1.0,
            max_timeout=10.0,
            adaptive_enabled=True,
            adjustment_factor=10.0,
        )
        manager = TimeoutManager(config)

        for i in range(15):
            await manager.record_response_time("SlowMethod", 100.0)

        timeout = await manager.get_timeout("SlowMethod")

        assert timeout <= config.max_timeout
