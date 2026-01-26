"""
Circuit Breaker Interceptor for gRPC
Phase 3: Resilience

Circuit Breaker 패턴:
- CLOSED: 정상 상태, 요청 통과
- OPEN: 실패 임계치 초과, 즉시 실패 반환
- HALF_OPEN: 복구 테스트 중, 일부 요청만 통과
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Set

import grpc
from grpc import StatusCode

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit Breaker 상태"""

    CLOSED = "closed"  # 정상 - 요청 통과
    OPEN = "open"  # 차단 - 즉시 실패
    HALF_OPEN = "half_open"  # 복구 테스트 중


class CircuitBreakerOpenError(Exception):
    """Circuit Breaker가 OPEN 상태일 때 발생"""

    def __init__(self, service_name: str, reset_timeout: float):
        self.service_name = service_name
        self.reset_timeout = reset_timeout
        super().__init__(
            f"Circuit breaker is OPEN for service '{service_name}'. "
            f"Reset in {reset_timeout:.1f}s"
        )


@dataclass
class CircuitBreakerConfig:
    """Circuit Breaker 설정"""

    failure_threshold: int = 3  # OPEN 전환 실패 횟수
    success_threshold: int = 2  # CLOSED 전환 성공 횟수
    reset_timeout: float = 30.0  # OPEN → HALF_OPEN 전환 대기 시간 (초)
    half_open_max_calls: int = 3  # HALF_OPEN에서 허용할 최대 동시 요청

    # 실패로 카운트할 gRPC 상태 코드 (시스템 에러만)
    failure_status_codes: Set[StatusCode] = field(
        default_factory=lambda: {
            StatusCode.UNAVAILABLE,
            StatusCode.DEADLINE_EXCEEDED,
            StatusCode.RESOURCE_EXHAUSTED,
            StatusCode.INTERNAL,
            StatusCode.UNKNOWN,
        }
    )


class CircuitBreaker:
    """
    Circuit Breaker 구현

    상태 전이:
    - CLOSED → OPEN: failure_count >= failure_threshold
    - OPEN → HALF_OPEN: reset_timeout 경과
    - HALF_OPEN → CLOSED: success_count >= success_threshold
    - HALF_OPEN → OPEN: 실패 발생
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()

        # 상태
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0

        # 동기화
        self._lock = asyncio.Lock()

        # 메트릭
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._state_changes: list = []

        logger.info(f"CircuitBreaker '{name}' initialized: {self.config}")

    @property
    def state(self) -> CircuitBreakerState:
        """현재 상태 반환 (자동 상태 전이 체크)"""
        if self._state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                return CircuitBreakerState.HALF_OPEN
        return self._state

    def _should_attempt_reset(self) -> bool:
        """OPEN → HALF_OPEN 전환 조건 확인"""
        if self._last_failure_time is None:
            return False
        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.config.reset_timeout

    async def can_execute(self) -> bool:
        """요청 실행 가능 여부 확인"""
        async with self._lock:
            current_state = self.state

            if current_state == CircuitBreakerState.CLOSED:
                return True

            if current_state == CircuitBreakerState.OPEN:
                return False

            # HALF_OPEN: 제한된 요청만 허용
            if current_state == CircuitBreakerState.HALF_OPEN:
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False

            return False

    async def record_success(self):
        """성공 기록"""
        async with self._lock:
            self._total_calls += 1
            self._total_successes += 1

            current_state = self.state

            if current_state == CircuitBreakerState.HALF_OPEN:
                self._success_count += 1
                logger.debug(
                    f"CircuitBreaker '{self.name}' HALF_OPEN success: "
                    f"{self._success_count}/{self.config.success_threshold}"
                )

                if self._success_count >= self.config.success_threshold:
                    self._transition_to(CircuitBreakerState.CLOSED)

            elif current_state == CircuitBreakerState.CLOSED:
                # 성공 시 실패 카운트 감소 (점진적 복구)
                if self._failure_count > 0:
                    self._failure_count -= 1

    async def record_failure(self, status_code: Optional[StatusCode] = None):
        """실패 기록"""
        # 설정된 상태 코드만 실패로 카운트
        if status_code and status_code not in self.config.failure_status_codes:
            logger.debug(
                f"CircuitBreaker '{self.name}': Status {status_code} not counted as failure"
            )
            return

        async with self._lock:
            self._total_calls += 1
            self._total_failures += 1
            self._last_failure_time = time.time()

            current_state = self.state

            if current_state == CircuitBreakerState.HALF_OPEN:
                # HALF_OPEN에서 실패 → 즉시 OPEN
                logger.warning(
                    f"CircuitBreaker '{self.name}' failure in HALF_OPEN, reopening"
                )
                self._transition_to(CircuitBreakerState.OPEN)

            elif current_state == CircuitBreakerState.CLOSED:
                self._failure_count += 1
                logger.debug(
                    f"CircuitBreaker '{self.name}' failure: "
                    f"{self._failure_count}/{self.config.failure_threshold}"
                )

                if self._failure_count >= self.config.failure_threshold:
                    self._transition_to(CircuitBreakerState.OPEN)

    def _transition_to(self, new_state: CircuitBreakerState):
        """상태 전이"""
        old_state = self._state
        self._state = new_state

        # 카운터 리셋
        if new_state == CircuitBreakerState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
        elif new_state == CircuitBreakerState.HALF_OPEN:
            self._success_count = 0
            self._half_open_calls = 0
        elif new_state == CircuitBreakerState.OPEN:
            self._success_count = 0
            self._half_open_calls = 0

        # 상태 변경 기록
        self._state_changes.append(
            {
                "from": old_state.value,
                "to": new_state.value,
                "timestamp": time.time(),
            }
        )

        logger.warning(
            f"CircuitBreaker '{self.name}' state: {old_state.value} → {new_state.value}"
        )

    def get_metrics(self) -> Dict[str, Any]:
        """메트릭 반환"""
        return {
            "name": self.name,
            "state": self.state.value,
            "total_calls": self._total_calls,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "state_changes": len(self._state_changes),
            "last_failure_time": self._last_failure_time,
        }

    async def reset(self):
        """수동 리셋"""
        async with self._lock:
            self._transition_to(CircuitBreakerState.CLOSED)
            logger.info(f"CircuitBreaker '{self.name}' manually reset")


class CircuitBreakerInterceptor(grpc.aio.UnaryUnaryClientInterceptor):
    """
    gRPC Client Interceptor for Circuit Breaker

    Usage:
        breaker = CircuitBreaker("claude-service")
        interceptor = CircuitBreakerInterceptor(breaker)
        channel = grpc.aio.insecure_channel(
            "localhost:5011",
            interceptors=[interceptor]
        )
    """

    def __init__(
        self,
        circuit_breaker: CircuitBreaker,
        fallback: Optional[Callable] = None,
    ):
        self.circuit_breaker = circuit_breaker
        self.fallback = fallback

    async def intercept_unary_unary(
        self,
        continuation: Callable,
        client_call_details: grpc.aio.ClientCallDetails,
        request: Any,
    ) -> Any:
        """Unary-Unary 요청 인터셉트"""

        # Circuit Breaker 상태 확인
        if not await self.circuit_breaker.can_execute():
            state = self.circuit_breaker.state

            if state == CircuitBreakerState.OPEN:
                reset_time = self.circuit_breaker.config.reset_timeout - (
                    time.time() - (self.circuit_breaker._last_failure_time or 0)
                )

                # Fallback이 있으면 실행
                if self.fallback:
                    logger.warning(
                        f"Circuit breaker OPEN, using fallback for "
                        f"{client_call_details.method}"
                    )
                    return await self.fallback(request)

                # Fallback 없으면 에러
                raise CircuitBreakerOpenError(
                    self.circuit_breaker.name, max(0, reset_time)
                )

            # HALF_OPEN에서 최대 호출 초과
            logger.warning(
                f"Circuit breaker HALF_OPEN at capacity for "
                f"{client_call_details.method}"
            )
            if self.fallback:
                return await self.fallback(request)
            raise CircuitBreakerOpenError(self.circuit_breaker.name, 0)

        try:
            # 실제 호출
            response = await continuation(client_call_details, request)

            # 성공 기록
            await self.circuit_breaker.record_success()

            return response

        except grpc.aio.AioRpcError as e:
            # 실패 기록 (상태 코드 기반)
            await self.circuit_breaker.record_failure(e.code())
            raise


class CircuitBreakerStreamInterceptor(grpc.aio.UnaryStreamClientInterceptor):
    """
    gRPC Client Interceptor for Circuit Breaker (Streaming)
    """

    def __init__(
        self,
        circuit_breaker: CircuitBreaker,
        fallback: Optional[Callable] = None,
    ):
        self.circuit_breaker = circuit_breaker
        self.fallback = fallback

    async def intercept_unary_stream(
        self,
        continuation: Callable,
        client_call_details: grpc.aio.ClientCallDetails,
        request: Any,
    ) -> Any:
        """Unary-Stream 요청 인터셉트"""

        if not await self.circuit_breaker.can_execute():
            state = self.circuit_breaker.state

            if state == CircuitBreakerState.OPEN:
                reset_time = self.circuit_breaker.config.reset_timeout - (
                    time.time() - (self.circuit_breaker._last_failure_time or 0)
                )
                raise CircuitBreakerOpenError(
                    self.circuit_breaker.name, max(0, reset_time)
                )

        try:
            response = await continuation(client_call_details, request)
            await self.circuit_breaker.record_success()
            return response

        except grpc.aio.AioRpcError as e:
            await self.circuit_breaker.record_failure(e.code())
            raise
