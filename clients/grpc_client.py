"""
gRPC 클라이언트
asyncio 기반 고성능 클라이언트
"""
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

# 경로 설정
from pathlib import Path
from typing import Any

import grpc

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.grpc_generated import ai_agent_pb2, ai_agent_pb2_grpc


@dataclass
class GrpcConnectionConfig:
    """gRPC 연결 설정"""
    host: str = "127.0.0.1"
    port: int = 5011
    timeout: float = 30.0
    compression: bool = True


class GrpcBaseClient:
    """gRPC 베이스 클라이언트"""

    def __init__(self, config: GrpcConnectionConfig):
        self.config = config
        self.channel: grpc.aio.Channel | None = None
        self._connected = False

        # 로깅
        self.logger = logging.getLogger(f"grpc.client.{config.host}:{config.port}")

    @property
    def address(self) -> str:
        return f"{self.config.host}:{self.config.port}"

    @property
    def is_connected(self) -> bool:
        return self._connected and self.channel is not None

    async def connect(self) -> bool:
        """연결"""
        if self._connected:
            return True

        try:
            options = [
                ("grpc.max_send_message_length", 50 * 1024 * 1024),
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),
            ]

            compression = grpc.Compression.Gzip if self.config.compression else grpc.Compression.NoCompression

            self.channel = grpc.aio.insecure_channel(
                self.address,
                options=options,
                compression=compression,
            )

            self._connected = True
            self.logger.info(f"Connected to {self.address}")
            return True

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False

    async def disconnect(self):
        """연결 종료"""
        if self.channel:
            await self.channel.close()
            self.channel = None
            self._connected = False
            self.logger.info("Disconnected")

    @asynccontextmanager
    async def session(self):
        """세션 컨텍스트"""
        await self.connect()
        try:
            yield self
        finally:
            await self.disconnect()


class ClaudeGrpcClient(GrpcBaseClient):
    """Claude gRPC 클라이언트"""

    def __init__(self, host: str = "127.0.0.1", port: int = 5011):
        super().__init__(GrpcConnectionConfig(host=host, port=port))
        self._stub: ai_agent_pb2_grpc.ClaudeServiceStub | None = None

    @property
    def stub(self) -> ai_agent_pb2_grpc.ClaudeServiceStub:
        if not self._stub and self.channel:
            self._stub = ai_agent_pb2_grpc.ClaudeServiceStub(self.channel)
        return self._stub

    async def health_check(self) -> dict[str, Any]:
        """헬스 체크"""
        request = ai_agent_pb2.HealthCheckRequest(service="claude")
        response = await self.stub.HealthCheck(
            request, timeout=self.config.timeout
        )
        return {
            "status": ai_agent_pb2.HealthCheckResponse.ServingStatus.Name(response.status),
            "version": response.version,
            "uptime_seconds": response.uptime_seconds,
        }

    async def create_plan(
        self,
        task: str,
        constraints: list = None,
    ) -> dict[str, Any]:
        """계획 수립"""
        request = ai_agent_pb2.PlanRequest(
            task_description=task,
            constraints=constraints or [],
        )
        response = await self.stub.CreatePlan(
            request, timeout=self.config.timeout
        )
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

    async def generate_code(
        self,
        description: str,
        language: str = "python",
    ) -> dict[str, Any]:
        """코드 생성"""
        request = ai_agent_pb2.GenerateCodeRequest(
            description=description,
            language=language,
        )
        response = await self.stub.GenerateCode(
            request, timeout=self.config.timeout
        )
        return {
            "language": response.language,
            "code": response.code,
            "description": response.description,
            "generated_at": response.generated_at,
        }

    async def stream_plan(
        self,
        task: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """스트리밍 계획 수립"""
        request = ai_agent_pb2.PlanRequest(task_description=task)

        async for message in self.stub.StreamPlan(request):
            yield {
                "stream_id": message.stream_id,
                "type": message.type,
                "content": message.content,
                "progress_percent": message.progress_percent,
                "timestamp": message.timestamp,
            }


class GeminiGrpcClient(GrpcBaseClient):
    """Gemini gRPC 클라이언트"""

    def __init__(self, host: str = "127.0.0.1", port: int = 5012):
        super().__init__(GrpcConnectionConfig(host=host, port=port))
        self._stub: ai_agent_pb2_grpc.GeminiServiceStub | None = None

    @property
    def stub(self) -> ai_agent_pb2_grpc.GeminiServiceStub:
        if not self._stub and self.channel:
            self._stub = ai_agent_pb2_grpc.GeminiServiceStub(self.channel)
        return self._stub

    async def health_check(self) -> dict[str, Any]:
        """헬스 체크"""
        request = ai_agent_pb2.HealthCheckRequest(service="gemini")
        response = await self.stub.HealthCheck(
            request, timeout=self.config.timeout
        )
        return {
            "status": ai_agent_pb2.HealthCheckResponse.ServingStatus.Name(response.status),
            "version": response.version,
            "uptime_seconds": response.uptime_seconds,
        }

    async def analyze(
        self,
        content: str,
        analysis_type: str = "general",
    ) -> dict[str, Any]:
        """분석"""
        request = ai_agent_pb2.AnalyzeRequest(
            content=content,
            analysis_type=analysis_type,
        )
        response = await self.stub.Analyze(
            request, timeout=self.config.timeout
        )
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

    async def review_code(
        self,
        code: str,
        language: str = "python",
    ) -> dict[str, Any]:
        """코드 리뷰"""
        request = ai_agent_pb2.ReviewCodeRequest(
            code=code,
            language=language,
            review_type="comprehensive",
        )
        response = await self.stub.ReviewCode(
            request, timeout=self.config.timeout
        )
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


class CodexGrpcClient(GrpcBaseClient):
    """Codex gRPC 클라이언트"""

    def __init__(self, host: str = "127.0.0.1", port: int = 5013):
        super().__init__(GrpcConnectionConfig(host=host, port=port))
        self._stub: ai_agent_pb2_grpc.CodexServiceStub | None = None

    @property
    def stub(self) -> ai_agent_pb2_grpc.CodexServiceStub:
        if not self._stub and self.channel:
            self._stub = ai_agent_pb2_grpc.CodexServiceStub(self.channel)
        return self._stub

    async def health_check(self) -> dict[str, Any]:
        """헬스 체크"""
        request = ai_agent_pb2.HealthCheckRequest(service="codex")
        response = await self.stub.HealthCheck(
            request, timeout=self.config.timeout
        )
        return {
            "status": ai_agent_pb2.HealthCheckResponse.ServingStatus.Name(response.status),
            "version": response.version,
            "uptime_seconds": response.uptime_seconds,
        }

    async def execute(
        self,
        command: str,
        working_dir: str = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """명령 실행"""
        import os
        request = ai_agent_pb2.ExecuteRequest(
            command=command,
            working_dir=working_dir or os.getcwd(),
            timeout_seconds=timeout,
        )
        response = await self.stub.Execute(
            request, timeout=self.config.timeout
        )
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
        self,
        command: str,
        working_dir: str = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """스트리밍 실행"""
        import os
        request = ai_agent_pb2.ExecuteRequest(
            command=command,
            working_dir=working_dir or os.getcwd(),
        )

        async for message in self.stub.StreamExecute(request):
            yield {
                "stream_id": message.stream_id,
                "type": message.type,
                "content": message.content,
                "progress_percent": message.progress_percent,
                "timestamp": message.timestamp,
            }


# 팩토리 함수
def create_grpc_client(service_name: str, host: str = "127.0.0.1"):
    """gRPC 클라이언트 생성"""
    clients = {
        "claude": (ClaudeGrpcClient, 5011),
        "gemini": (GeminiGrpcClient, 5012),
        "codex": (CodexGrpcClient, 5013),
    }

    if service_name not in clients:
        raise ValueError(f"Unknown service: {service_name}")

    client_class, port = clients[service_name]
    return client_class(host=host, port=port)
