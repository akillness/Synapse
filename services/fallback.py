"""
Fallback Mechanism for gRPC Services
Phase 3: Resilience

서비스 장애 시 대체 응답 제공:
- 캐시된 응답 반환
- Rule-based 기본 응답
- 서비스별 커스텀 폴백
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """캐시 엔트리"""

    value: T
    timestamp: float
    ttl: float

    @property
    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl


@dataclass
class FallbackConfig:
    """폴백 설정"""

    cache_enabled: bool = True
    cache_ttl: float = 300.0
    max_cache_size: int = 1000
    rule_based_enabled: bool = True


class FallbackCache:
    """응답 캐시 관리자"""

    def __init__(self, config: FallbackConfig | None = None):
        self.config = config or FallbackConfig()
        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    def _make_key(self, method: str, request: Any) -> str:
        """캐시 키 생성"""
        request_str = str(request) if request else ""
        return f"{method}:{hash(request_str)}"

    async def get(self, method: str, request: Any) -> Any | None:
        """캐시 조회"""
        if not self.config.cache_enabled:
            return None

        key = self._make_key(method, request)

        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                return None

            if entry.is_expired:
                del self._cache[key]
                return None

            logger.debug(f"Cache hit for {method}")
            return entry.value

    async def set(
        self,
        method: str,
        request: Any,
        response: Any,
        ttl: float | None = None,
    ):
        """캐시 저장"""
        if not self.config.cache_enabled:
            return

        key = self._make_key(method, request)

        async with self._lock:
            if len(self._cache) >= self.config.max_cache_size:
                await self._evict_oldest()

            self._cache[key] = CacheEntry(
                value=response,
                timestamp=time.time(),
                ttl=ttl or self.config.cache_ttl,
            )
            logger.debug(f"Cached response for {method}")

    async def _evict_oldest(self):
        """가장 오래된 캐시 제거"""
        if not self._cache:
            return

        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].timestamp)
        del self._cache[oldest_key]

    async def clear(self):
        """캐시 전체 삭제"""
        async with self._lock:
            self._cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """캐시 통계"""
        return {
            "size": len(self._cache),
            "max_size": self.config.max_cache_size,
            "ttl": self.config.cache_ttl,
        }


class FallbackHandler(ABC):
    """폴백 핸들러 베이스 클래스"""

    @abstractmethod
    async def handle(self, method: str, request: Any) -> Any | None:
        """폴백 응답 생성"""
        pass


class RuleBasedFallback(FallbackHandler):
    """Rule-based 폴백 핸들러"""

    def __init__(self):
        self._rules: dict[str, Callable[[Any], Any]] = {}

    def register_rule(self, method_pattern: str, handler: Callable[[Any], Any]):
        """폴백 규칙 등록"""
        self._rules[method_pattern] = handler

    async def handle(self, method: str, request: Any) -> Any | None:
        """규칙 기반 폴백 응답"""
        method_name = method.split("/")[-1] if "/" in method else method

        for pattern, handler in self._rules.items():
            if pattern in method_name:
                try:
                    result = handler(request)
                    if asyncio.iscoroutine(result):
                        result = await result
                    logger.info(f"Rule-based fallback triggered for {method}")
                    return result
                except Exception as e:
                    logger.error(f"Fallback rule error for {method}: {e}")

        return None


class FallbackManager:
    """통합 폴백 관리자"""

    def __init__(self, config: FallbackConfig | None = None):
        self.config = config or FallbackConfig()
        self.cache = FallbackCache(self.config)
        self.rule_handler = RuleBasedFallback()
        self._custom_handlers: dict[str, FallbackHandler] = {}

    def register_handler(self, service_name: str, handler: FallbackHandler):
        """서비스별 커스텀 핸들러 등록"""
        self._custom_handlers[service_name] = handler

    def register_rule(self, method_pattern: str, handler: Callable[[Any], Any]):
        """폴백 규칙 등록"""
        self.rule_handler.register_rule(method_pattern, handler)

    async def get_fallback(
        self,
        service_name: str,
        method: str,
        request: Any,
    ) -> Any | None:
        """폴백 응답 조회"""
        cached = await self.cache.get(method, request)
        if cached is not None:
            return cached

        if service_name in self._custom_handlers:
            result = await self._custom_handlers[service_name].handle(method, request)
            if result is not None:
                return result

        if self.config.rule_based_enabled:
            result = await self.rule_handler.handle(method, request)
            if result is not None:
                return result

        return None

    async def cache_response(
        self,
        method: str,
        request: Any,
        response: Any,
        ttl: float | None = None,
    ):
        """성공 응답 캐싱"""
        await self.cache.set(method, request, response, ttl)


class ClaudeFallbackHandler(FallbackHandler):
    """Claude 서비스 전용 폴백"""

    async def handle(self, method: str, request: Any) -> Any | None:
        method_name = method.split("/")[-1] if "/" in method else method

        if method_name == "HealthCheck":
            return {
                "status": "DEGRADED",
                "version": "fallback",
                "message": "Service temporarily unavailable",
            }

        if method_name == "CreatePlan":
            return {
                "task": getattr(request, "task_description", "unknown"),
                "steps": [
                    {"order": 1, "phase": "Fallback", "action": "Retry later"},
                ],
                "total_steps": 1,
                "message": "Fallback plan - service temporarily unavailable",
            }

        return None


class GeminiFallbackHandler(FallbackHandler):
    """Gemini 서비스 전용 폴백"""

    async def handle(self, method: str, request: Any) -> Any | None:
        method_name = method.split("/")[-1] if "/" in method else method

        if method_name == "HealthCheck":
            return {
                "status": "DEGRADED",
                "version": "fallback",
            }

        if method_name == "Analyze":
            return {
                "analysis_type": getattr(request, "analysis_type", "unknown"),
                "summary": "Analysis unavailable - service temporarily down",
                "findings": [],
            }

        return None


class CodexFallbackHandler(FallbackHandler):
    """Codex 서비스 전용 폴백"""

    async def handle(self, method: str, request: Any) -> Any | None:
        method_name = method.split("/")[-1] if "/" in method else method

        if method_name == "HealthCheck":
            return {
                "status": "DEGRADED",
                "version": "fallback",
            }

        if method_name == "Execute":
            return {
                "success": False,
                "command": getattr(request, "command", "unknown"),
                "stderr": "Execution unavailable - service temporarily down",
                "exit_code": -1,
            }

        return None


def create_default_fallback_manager() -> FallbackManager:
    """기본 폴백 매니저 생성"""
    manager = FallbackManager()

    manager.register_handler("claude", ClaudeFallbackHandler())
    manager.register_handler("gemini", GeminiFallbackHandler())
    manager.register_handler("codex", CodexFallbackHandler())

    return manager
