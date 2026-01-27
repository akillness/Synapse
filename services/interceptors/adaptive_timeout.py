"""
Adaptive Timeout Interceptor for gRPC
Phase 3: Resilience

작업 난이도/타입에 따른 동적 타임아웃 설정:
- 간단한 작업 (health check): 짧은 타임아웃
- 복잡한 작업 (code generation): 긴 타임아웃
- 응답 시간 기반 자동 조정
"""

import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import grpc

logger = logging.getLogger(__name__)


@dataclass
class TimeoutConfig:
    """타임아웃 설정"""

    default_timeout: float = 30.0
    min_timeout: float = 5.0
    max_timeout: float = 120.0

    method_timeouts: dict[str, float] = field(
        default_factory=lambda: {
            "HealthCheck": 5.0,
            "CreatePlan": 60.0,
            "GenerateCode": 90.0,
            "StreamPlan": 120.0,
            "Analyze": 45.0,
            "ReviewCode": 60.0,
            "Execute": 30.0,
            "StreamExecute": 120.0,
        }
    )

    adaptive_enabled: bool = True
    percentile: float = 95.0
    history_size: int = 100
    adjustment_factor: float = 1.5


class TimeoutManager:
    """응답 시간 기반 동적 타임아웃 관리"""

    def __init__(self, config: TimeoutConfig | None = None):
        self.config = config or TimeoutConfig()
        self._response_times: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def record_response_time(self, method: str, duration: float):
        """응답 시간 기록"""
        async with self._lock:
            history = self._response_times[method]
            history.append(duration)

            if len(history) > self.config.history_size:
                history.pop(0)

    def _get_percentile(self, data: list[float], percentile: float) -> float:
        """백분위수 계산"""
        if not data:
            return self.config.default_timeout

        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        index = min(index, len(sorted_data) - 1)
        return sorted_data[index]

    def _extract_method_name(self, full_method: str | bytes) -> str:
        """gRPC 메서드 경로에서 메서드 이름 추출"""
        if isinstance(full_method, bytes):
            full_method = full_method.decode("utf-8")
        if "/" in full_method:
            return full_method.split("/")[-1]
        return full_method

    async def get_timeout(self, method: str) -> float:
        """메서드별 적응형 타임아웃 반환"""
        method_name = self._extract_method_name(method)

        base_timeout = self.config.method_timeouts.get(method_name, self.config.default_timeout)

        if not self.config.adaptive_enabled:
            return base_timeout

        async with self._lock:
            history = self._response_times.get(method_name, [])

            if len(history) < 10:
                return base_timeout

            p95_time = self._get_percentile(history, self.config.percentile)
            adaptive_timeout = p95_time * self.config.adjustment_factor

            final_timeout = max(
                self.config.min_timeout,
                min(adaptive_timeout, self.config.max_timeout, base_timeout * 2),
            )

            logger.debug(
                f"Adaptive timeout for {method_name}: "
                f"base={base_timeout:.1f}s, p95={p95_time:.1f}s, "
                f"final={final_timeout:.1f}s"
            )

            return final_timeout

    def get_metrics(self) -> dict[str, Any]:
        """메트릭 반환"""
        metrics = {}
        for method, times in self._response_times.items():
            if times:
                metrics[method] = {
                    "count": len(times),
                    "avg": sum(times) / len(times),
                    "min": min(times),
                    "max": max(times),
                    "p95": self._get_percentile(times, 95),
                }
        return metrics


class AdaptiveTimeoutInterceptor(grpc.aio.UnaryUnaryClientInterceptor):
    """
    gRPC Client Interceptor for Adaptive Timeout

    응답 시간 히스토리 기반으로 타임아웃 자동 조정
    """

    def __init__(
        self,
        timeout_manager: TimeoutManager | None = None,
        config: TimeoutConfig | None = None,
    ):
        self.timeout_manager = timeout_manager or TimeoutManager(config)

    async def intercept_unary_unary(
        self,
        continuation: Callable,
        client_call_details: grpc.aio.ClientCallDetails,
        request: Any,
    ) -> Any:
        """Unary-Unary 요청 인터셉트 및 동적 타임아웃 적용"""

        method = client_call_details.method or ""

        timeout = await self.timeout_manager.get_timeout(method)

        new_details = grpc.aio.ClientCallDetails(
            method=client_call_details.method,
            timeout=timeout,
            metadata=client_call_details.metadata,
            credentials=client_call_details.credentials,
            wait_for_ready=client_call_details.wait_for_ready,
        )

        start_time = time.perf_counter()

        try:
            response = await continuation(new_details, request)

            duration = time.perf_counter() - start_time
            await self.timeout_manager.record_response_time(method, duration)

            return response

        except grpc.aio.AioRpcError:
            duration = time.perf_counter() - start_time
            await self.timeout_manager.record_response_time(method, duration)
            raise


class AdaptiveTimeoutStreamInterceptor(grpc.aio.UnaryStreamClientInterceptor):
    """gRPC Client Interceptor for Adaptive Timeout (Streaming)"""

    def __init__(
        self,
        timeout_manager: TimeoutManager | None = None,
        config: TimeoutConfig | None = None,
    ):
        self.timeout_manager = timeout_manager or TimeoutManager(config)

    async def intercept_unary_stream(
        self,
        continuation: Callable,
        client_call_details: grpc.aio.ClientCallDetails,
        request: Any,
    ) -> Any:
        """Unary-Stream 요청 인터셉트 및 동적 타임아웃 적용"""

        method = client_call_details.method or ""

        timeout = await self.timeout_manager.get_timeout(method)

        new_details = grpc.aio.ClientCallDetails(
            method=client_call_details.method,
            timeout=timeout,
            metadata=client_call_details.metadata,
            credentials=client_call_details.credentials,
            wait_for_ready=client_call_details.wait_for_ready,
        )

        return await continuation(new_details, request)
