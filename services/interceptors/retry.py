"""
Retry Interceptor with Exponential Backoff for gRPC
Phase 3: Resilience

gRPC 공식 Backoff 알고리즘 구현:
- INITIAL_BACKOFF: 첫 실패 후 대기 시간
- MULTIPLIER: 재시도마다 backoff 증가 배수
- JITTER: 동시 재시도 방지를 위한 랜덤 요소
- MAX_BACKOFF: 최대 대기 시간
"""

import asyncio
import logging
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import grpc
from grpc import StatusCode

logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    """재시도 정책 설정"""

    max_attempts: int = 4
    initial_backoff: float = 1.0
    max_backoff: float = 30.0
    backoff_multiplier: float = 2.0
    jitter: float = 0.2

    retryable_status_codes: set[StatusCode] = field(
        default_factory=lambda: {
            StatusCode.UNAVAILABLE,
            StatusCode.DEADLINE_EXCEEDED,
            StatusCode.RESOURCE_EXHAUSTED,
            StatusCode.ABORTED,
        }
    )


class RetryInterceptor(grpc.aio.UnaryUnaryClientInterceptor):
    """
    gRPC Client Interceptor for Retry with Exponential Backoff

    gRPC 표준 backoff 알고리즘 적용:
    current_backoff = min(initial_backoff * (multiplier ^ attempt), max_backoff)
    sleep_time = current_backoff + uniform(-jitter * current_backoff, jitter * current_backoff)
    """

    def __init__(
        self,
        policy: RetryPolicy | None = None,
        on_retry: Callable[[int, Exception, float], None] | None = None,
    ):
        self.policy = policy or RetryPolicy()
        self.on_retry = on_retry

        self._total_retries = 0
        self._successful_retries = 0

    def _calculate_backoff(self, attempt: int) -> float:
        """Exponential backoff with jitter 계산"""
        backoff = min(
            self.policy.initial_backoff * (self.policy.backoff_multiplier**attempt),
            self.policy.max_backoff,
        )
        jitter_range = self.policy.jitter * backoff
        return backoff + random.uniform(-jitter_range, jitter_range)

    def _is_retryable(self, status_code: StatusCode) -> bool:
        """재시도 가능한 에러인지 확인"""
        return status_code in self.policy.retryable_status_codes

    async def intercept_unary_unary(
        self,
        continuation: Callable,
        client_call_details: grpc.aio.ClientCallDetails,
        request: Any,
    ) -> Any:
        """Unary-Unary 요청 인터셉트 및 재시도"""

        last_exception: Exception | None = None

        for attempt in range(self.policy.max_attempts):
            try:
                response = await continuation(client_call_details, request)

                if attempt > 0:
                    self._successful_retries += 1
                    logger.info(
                        f"Retry succeeded on attempt {attempt + 1} for "
                        f"{client_call_details.method}"
                    )

                return response

            except grpc.aio.AioRpcError as e:
                last_exception = e

                if not self._is_retryable(e.code()):
                    logger.debug(
                        f"Non-retryable error {e.code()} for {client_call_details.method}"
                    )
                    raise

                if attempt < self.policy.max_attempts - 1:
                    self._total_retries += 1
                    backoff = self._calculate_backoff(attempt)

                    logger.warning(
                        f"Retry {attempt + 1}/{self.policy.max_attempts} for "
                        f"{client_call_details.method} after {e.code()}, "
                        f"waiting {backoff:.2f}s"
                    )

                    if self.on_retry:
                        self.on_retry(attempt + 1, e, backoff)

                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        f"All {self.policy.max_attempts} retries exhausted for "
                        f"{client_call_details.method}"
                    )

        if last_exception:
            raise last_exception

        raise RuntimeError("Unexpected retry loop exit")

    def get_metrics(self) -> dict:
        """재시도 메트릭 반환"""
        return {
            "total_retries": self._total_retries,
            "successful_retries": self._successful_retries,
            "policy": {
                "max_attempts": self.policy.max_attempts,
                "initial_backoff": self.policy.initial_backoff,
                "max_backoff": self.policy.max_backoff,
                "backoff_multiplier": self.policy.backoff_multiplier,
            },
        }


class RetryStreamInterceptor(grpc.aio.UnaryStreamClientInterceptor):
    """
    gRPC Client Interceptor for Retry (Streaming)

    스트리밍의 경우 전체 스트림 재시도
    """

    def __init__(
        self,
        policy: RetryPolicy | None = None,
        on_retry: Callable[[int, Exception, float], None] | None = None,
    ):
        self.policy = policy or RetryPolicy()
        self.on_retry = on_retry

    def _calculate_backoff(self, attempt: int) -> float:
        backoff = min(
            self.policy.initial_backoff * (self.policy.backoff_multiplier**attempt),
            self.policy.max_backoff,
        )
        jitter_range = self.policy.jitter * backoff
        return backoff + random.uniform(-jitter_range, jitter_range)

    def _is_retryable(self, status_code: StatusCode) -> bool:
        return status_code in self.policy.retryable_status_codes

    async def intercept_unary_stream(
        self,
        continuation: Callable,
        client_call_details: grpc.aio.ClientCallDetails,
        request: Any,
    ) -> Any:
        """Unary-Stream 요청 인터셉트 및 재시도"""

        last_exception: Exception | None = None

        for attempt in range(self.policy.max_attempts):
            try:
                response = await continuation(client_call_details, request)
                return response

            except grpc.aio.AioRpcError as e:
                last_exception = e

                if not self._is_retryable(e.code()):
                    raise

                if attempt < self.policy.max_attempts - 1:
                    backoff = self._calculate_backoff(attempt)

                    logger.warning(
                        f"Stream retry {attempt + 1}/{self.policy.max_attempts} for "
                        f"{client_call_details.method}, waiting {backoff:.2f}s"
                    )

                    if self.on_retry:
                        self.on_retry(attempt + 1, e, backoff)

                    await asyncio.sleep(backoff)

        if last_exception:
            raise last_exception

        raise RuntimeError("Unexpected retry loop exit")
