"""
Resilient gRPC Client with Circuit Breaker, Retry, and Adaptive Timeout
Phase 3: Full Resilience Support
"""

import logging
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import grpc

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.fallback import FallbackManager, create_default_fallback_manager
from services.grpc_generated import ai_agent_pb2, ai_agent_pb2_grpc
from services.interceptors.adaptive_timeout import (
    AdaptiveTimeoutInterceptor,
    TimeoutConfig,
    TimeoutManager,
)
from services.interceptors.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerInterceptor,
)
from services.interceptors.retry import (
    RetryInterceptor,
    RetryPolicy,
)

logger = logging.getLogger(__name__)


@dataclass
class ResilienceConfig:
    circuit_breaker_enabled: bool = True
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_reset_timeout: float = 30.0

    retry_enabled: bool = True
    retry_max_attempts: int = 4
    retry_initial_backoff: float = 1.0
    retry_max_backoff: float = 30.0

    adaptive_timeout_enabled: bool = True
    default_timeout: float = 30.0

    fallback_enabled: bool = True


@dataclass
class ResilientClientConfig:
    host: str = "127.0.0.1"
    port: int = 5011
    service_name: str = "unknown"
    compression: bool = True
    resilience: ResilienceConfig = field(default_factory=ResilienceConfig)


class ResilientGrpcClient:
    def __init__(self, config: ResilientClientConfig):
        self.config = config
        self.channel: grpc.aio.Channel | None = None
        self._connected = False

        self.logger = logging.getLogger(f"resilient.{config.service_name}")

        self._circuit_breaker: CircuitBreaker | None = None
        self._timeout_manager: TimeoutManager | None = None
        self._fallback_manager: FallbackManager | None = None
        self._interceptors: list[grpc.aio.ClientInterceptor] = []

        self._setup_resilience()

    def _setup_resilience(self):
        res = self.config.resilience

        if res.circuit_breaker_enabled:
            cb_config = CircuitBreakerConfig(
                failure_threshold=res.circuit_breaker_failure_threshold,
                reset_timeout=res.circuit_breaker_reset_timeout,
            )
            self._circuit_breaker = CircuitBreaker(self.config.service_name, cb_config)
            self._interceptors.append(CircuitBreakerInterceptor(self._circuit_breaker))

        if res.retry_enabled:
            retry_policy = RetryPolicy(
                max_attempts=res.retry_max_attempts,
                initial_backoff=res.retry_initial_backoff,
                max_backoff=res.retry_max_backoff,
            )
            self._interceptors.append(RetryInterceptor(retry_policy))

        if res.adaptive_timeout_enabled:
            timeout_config = TimeoutConfig(default_timeout=res.default_timeout)
            self._timeout_manager = TimeoutManager(timeout_config)
            self._interceptors.append(AdaptiveTimeoutInterceptor(self._timeout_manager))

        if res.fallback_enabled:
            self._fallback_manager = create_default_fallback_manager()

    @property
    def address(self) -> str:
        return f"{self.config.host}:{self.config.port}"

    @property
    def is_connected(self) -> bool:
        return self._connected and self.channel is not None

    async def connect(self) -> bool:
        if self._connected:
            return True

        try:
            options = [
                ("grpc.max_send_message_length", 50 * 1024 * 1024),
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),
                ("grpc.keepalive_time_ms", 30000),
                ("grpc.keepalive_timeout_ms", 10000),
            ]

            compression = (
                grpc.Compression.Gzip if self.config.compression else grpc.Compression.NoCompression
            )

            self.channel = grpc.aio.insecure_channel(
                self.address,
                options=options,
                compression=compression,
                interceptors=self._interceptors,
            )

            self._connected = True
            self.logger.info(f"Connected to {self.address} with resilience enabled")
            return True

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False

    async def disconnect(self):
        if self.channel:
            await self.channel.close()
            self.channel = None
            self._connected = False
            self.logger.info("Disconnected")

    @asynccontextmanager
    async def session(self):
        await self.connect()
        try:
            yield self
        finally:
            await self.disconnect()

    def get_metrics(self) -> dict[str, Any]:
        metrics = {"service": self.config.service_name, "connected": self._connected}

        if self._circuit_breaker:
            metrics["circuit_breaker"] = self._circuit_breaker.get_metrics()

        if self._timeout_manager:
            metrics["timeout"] = self._timeout_manager.get_metrics()

        if self._fallback_manager:
            metrics["fallback_cache"] = self._fallback_manager.cache.get_stats()

        return metrics


class ResilientClaudeClient(ResilientGrpcClient):
    def __init__(self, host: str = "127.0.0.1", port: int = 5011):
        config = ResilientClientConfig(host=host, port=port, service_name="claude")
        super().__init__(config)
        self._stub: ai_agent_pb2_grpc.ClaudeServiceStub | None = None

    @property
    def stub(self) -> ai_agent_pb2_grpc.ClaudeServiceStub:
        if not self._stub and self.channel:
            self._stub = ai_agent_pb2_grpc.ClaudeServiceStub(self.channel)
        return self._stub

    async def health_check(self) -> dict[str, Any]:
        request = ai_agent_pb2.HealthCheckRequest(service="claude")
        response = await self.stub.HealthCheck(request)
        return {
            "status": ai_agent_pb2.HealthCheckResponse.ServingStatus.Name(response.status),
            "version": response.version,
            "uptime_seconds": response.uptime_seconds,
        }

    async def create_plan(self, task: str, constraints: list[str] | None = None) -> dict[str, Any]:
        request = ai_agent_pb2.PlanRequest(
            task_description=task,
            constraints=constraints or [],
        )
        response = await self.stub.CreatePlan(request)
        return {
            "task": response.task,
            "steps": [
                {
                    "order": step.order,
                    "phase": step.phase,
                    "action": step.action,
                    "agent": step.agent,
                    "description": step.description,
                }
                for step in response.steps
            ],
            "total_steps": response.total_steps,
            "estimated_agents": list(response.estimated_agents),
            "created_at": response.created_at,
        }

    async def generate_code(self, description: str, language: str = "python") -> dict[str, Any]:
        request = ai_agent_pb2.GenerateCodeRequest(description=description, language=language)
        response = await self.stub.GenerateCode(request)
        return {
            "language": response.language,
            "code": response.code,
            "description": response.description,
            "generated_at": response.generated_at,
        }

    async def stream_plan(self, task: str) -> AsyncIterator[dict[str, Any]]:
        request = ai_agent_pb2.PlanRequest(task_description=task)
        async for message in self.stub.StreamPlan(request):
            yield {
                "stream_id": message.stream_id,
                "type": message.type,
                "content": message.content,
                "progress_percent": message.progress_percent,
                "timestamp": message.timestamp,
            }


class ResilientGeminiClient(ResilientGrpcClient):
    def __init__(self, host: str = "127.0.0.1", port: int = 5012):
        config = ResilientClientConfig(host=host, port=port, service_name="gemini")
        super().__init__(config)
        self._stub: ai_agent_pb2_grpc.GeminiServiceStub | None = None

    @property
    def stub(self) -> ai_agent_pb2_grpc.GeminiServiceStub:
        if not self._stub and self.channel:
            self._stub = ai_agent_pb2_grpc.GeminiServiceStub(self.channel)
        return self._stub

    async def health_check(self) -> dict[str, Any]:
        request = ai_agent_pb2.HealthCheckRequest(service="gemini")
        response = await self.stub.HealthCheck(request)
        return {
            "status": ai_agent_pb2.HealthCheckResponse.ServingStatus.Name(response.status),
            "version": response.version,
            "uptime_seconds": response.uptime_seconds,
        }

    async def analyze(self, content: str, analysis_type: str = "general") -> dict[str, Any]:
        request = ai_agent_pb2.AnalyzeRequest(content=content, analysis_type=analysis_type)
        response = await self.stub.Analyze(request)
        return {
            "analysis_type": response.analysis_type,
            "content_length": response.content_length,
            "token_estimate": response.token_estimate,
            "findings": [
                {
                    "category": f.category,
                    "severity": f.severity,
                    "description": f.description,
                }
                for f in response.findings
            ],
            "summary": response.summary,
            "analyzed_at": response.analyzed_at,
        }

    async def review_code(self, code: str, language: str = "python") -> dict[str, Any]:
        request = ai_agent_pb2.ReviewCodeRequest(
            code=code, language=language, review_type="comprehensive"
        )
        response = await self.stub.ReviewCode(request)
        return {
            "language": response.language,
            "review_type": response.review_type,
            "code_length": response.code_length,
            "issues": [
                {
                    "type": i.type,
                    "severity": i.severity,
                    "line": i.line,
                    "message": i.message,
                }
                for i in response.issues
            ],
            "overall_score": response.overall_score,
            "reviewed_at": response.reviewed_at,
        }


class ResilientCodexClient(ResilientGrpcClient):
    def __init__(self, host: str = "127.0.0.1", port: int = 5013):
        config = ResilientClientConfig(host=host, port=port, service_name="codex")
        super().__init__(config)
        self._stub: ai_agent_pb2_grpc.CodexServiceStub | None = None

    @property
    def stub(self) -> ai_agent_pb2_grpc.CodexServiceStub:
        if not self._stub and self.channel:
            self._stub = ai_agent_pb2_grpc.CodexServiceStub(self.channel)
        return self._stub

    async def health_check(self) -> dict[str, Any]:
        request = ai_agent_pb2.HealthCheckRequest(service="codex")
        response = await self.stub.HealthCheck(request)
        return {
            "status": ai_agent_pb2.HealthCheckResponse.ServingStatus.Name(response.status),
            "version": response.version,
            "uptime_seconds": response.uptime_seconds,
        }

    async def execute(
        self, command: str, working_dir: str | None = None, timeout: int = 30
    ) -> dict[str, Any]:
        request = ai_agent_pb2.ExecuteRequest(
            command=command,
            working_dir=working_dir or os.getcwd(),
            timeout_seconds=timeout,
        )
        response = await self.stub.Execute(request)
        return {
            "success": response.success,
            "command": response.command,
            "exit_code": response.exit_code,
            "stdout": response.stdout,
            "stderr": response.stderr,
            "duration_seconds": response.duration_seconds,
            "executed_at": response.executed_at,
        }

    async def stream_execute(
        self, command: str, working_dir: str | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        request = ai_agent_pb2.ExecuteRequest(
            command=command, working_dir=working_dir or os.getcwd()
        )
        async for message in self.stub.StreamExecute(request):
            yield {
                "stream_id": message.stream_id,
                "type": message.type,
                "content": message.content,
                "progress_percent": message.progress_percent,
                "timestamp": message.timestamp,
            }


def create_resilient_client(service_name: str, host: str = "127.0.0.1") -> ResilientGrpcClient:
    clients = {
        "claude": (ResilientClaudeClient, 5011),
        "gemini": (ResilientGeminiClient, 5012),
        "codex": (ResilientCodexClient, 5013),
    }

    if service_name not in clients:
        raise ValueError(f"Unknown service: {service_name}")

    client_class, port = clients[service_name]
    return client_class(host=host, port=port)
