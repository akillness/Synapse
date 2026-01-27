"""
gRPC 베이스 서비스 클래스
asyncio 기반 고성능 서비스
"""

import asyncio
import logging
import signal
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

# 생성된 proto 모듈
from .grpc_generated import ai_agent_pb2, ai_agent_pb2_grpc


class GrpcBaseService(ABC):
    """gRPC 베이스 서비스 클래스"""

    def __init__(
        self,
        name: str,
        host: str = "0.0.0.0",
        port: int = 5001,
        max_workers: int = 10,
        log_level: str = "INFO",
    ):
        self.name = name
        self.host = host
        self.port = port
        self.max_workers = max_workers

        # 상태
        self.server: grpc.aio.Server | None = None
        self.start_time: float | None = None
        self._running = False

        # 헬스 체크
        self.health_servicer = health.aio.HealthServicer()

        # 로깅
        self.logger = logging.getLogger(f"grpc.{name}")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.logger.propagate = False

        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(
                logging.Formatter("%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s")
            )
            self.logger.addHandler(handler)

    async def start(self):
        """gRPC 서버 시작"""
        self._running = True
        self.start_time = time.time()

        # 서버 생성
        self.server = grpc.aio.server(
            options=[
                ("grpc.max_send_message_length", 50 * 1024 * 1024),  # 50MB
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),
                ("grpc.keepalive_time_ms", 30000),
                ("grpc.keepalive_timeout_ms", 10000),
                ("grpc.http2.min_ping_interval_without_data_ms", 5000),
            ],
            compression=grpc.Compression.Gzip,
        )

        # 서비스 등록
        self._register_services()

        # 헬스 체크 서비스 등록
        health_pb2_grpc.add_HealthServicer_to_server(self.health_servicer, self.server)

        # 포트 바인딩
        listen_addr = f"{self.host}:{self.port}"
        self.server.add_insecure_port(listen_addr)

        # 서버 시작
        await self.server.start()

        # 헬스 상태 설정
        await self._set_health_status(health_pb2.HealthCheckResponse.SERVING)

        self._print_banner()

        # 시그널 핸들러
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        # 종료 대기
        await self.server.wait_for_termination()

    async def stop(self):
        """서버 종료"""
        self.logger.info("Shutting down...")
        self._running = False

        # 헬스 상태 변경
        await self._set_health_status(health_pb2.HealthCheckResponse.NOT_SERVING)

        if self.server:
            # Graceful shutdown (5초 대기)
            await self.server.stop(5)

        self.logger.info("Server stopped")

    async def _set_health_status(self, status):
        """헬스 상태 설정"""
        service_name = f"ai_agent.{self.name.capitalize()}Service"
        await self.health_servicer.set(service_name, status)
        await self.health_servicer.set("", status)  # 전체 서버 상태

    def _print_banner(self):
        """시작 배너 출력"""
        int(time.time() - self.start_time) if self.start_time else 0
        banner = f"""
╔══════════════════════════════════════════════════════════════════╗
║  gRPC Service: {self.name.upper():<49} ║
║  Address: {self.host}:{self.port:<48} ║
║  Protocol: gRPC (HTTP/2 + Protobuf)                              ║
║  Compression: gzip                                               ║
╚══════════════════════════════════════════════════════════════════╝
"""
        self.logger.info(banner)

    @abstractmethod
    def _register_services(self):
        """서비스 등록 (서브클래스에서 구현)"""
        pass

    def get_uptime(self) -> int:
        """업타임 반환 (초)"""
        if self.start_time:
            return int(time.time() - self.start_time)
        return 0


class ClaudeGrpcServicer(ai_agent_pb2_grpc.ClaudeServiceServicer):
    """Claude gRPC 서비스 구현"""

    def __init__(self, service: "ClaudeGrpcService"):
        self.service = service
        self.logger = service.logger

    async def HealthCheck(
        self,
        request: ai_agent_pb2.HealthCheckRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_agent_pb2.HealthCheckResponse:
        """헬스 체크"""
        return ai_agent_pb2.HealthCheckResponse(
            status=ai_agent_pb2.HealthCheckResponse.ServingStatus.SERVING,
            version="1.0.0",
            uptime_seconds=self.service.get_uptime(),
            active_connections=0,
        )

    async def Process(
        self,
        request: ai_agent_pb2.AgentRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_agent_pb2.AgentResponse:
        """범용 처리"""
        self.logger.debug(f"Process: {request.method}")

        result = f"[Claude gRPC] Processed: {request.method}"

        return ai_agent_pb2.AgentResponse(
            request_id=request.request_id,
            success=True,
            result=result.encode("utf-8"),
            timestamp=int(time.time() * 1000),
        )

    async def CreatePlan(
        self,
        request: ai_agent_pb2.PlanRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_agent_pb2.PlanResponse:
        """계획 수립"""
        self.logger.info(f"CreatePlan: {request.task_description}")

        steps = [
            ai_agent_pb2.PlanResponse.PlanStep(
                order=1,
                phase="Analysis",
                action="Analyze requirements",
                agent="gemini",
                description="Gemini가 요구사항 분석",
            ),
            ai_agent_pb2.PlanResponse.PlanStep(
                order=2,
                phase="Design",
                action="Design architecture",
                agent="claude",
                description="Claude가 아키텍처 설계",
            ),
            ai_agent_pb2.PlanResponse.PlanStep(
                order=3,
                phase="Implementation",
                action="Generate code",
                agent="claude",
                description="Claude가 코드 생성",
            ),
            ai_agent_pb2.PlanResponse.PlanStep(
                order=4,
                phase="Testing",
                action="Run tests",
                agent="codex",
                description="Codex가 테스트 실행",
            ),
            ai_agent_pb2.PlanResponse.PlanStep(
                order=5,
                phase="Review",
                action="Review and document",
                agent="claude",
                description="Claude가 검토 및 문서화",
            ),
        ]

        return ai_agent_pb2.PlanResponse(
            task=request.task_description,
            steps=steps,
            total_steps=len(steps),
            estimated_agents=["claude", "gemini", "codex"],
            created_at=datetime.now().isoformat(),
        )

    async def GenerateCode(
        self,
        request: ai_agent_pb2.GenerateCodeRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_agent_pb2.GenerateCodeResponse:
        """코드 생성"""
        self.logger.info(f"GenerateCode: {request.language}")

        code = f'''"""
{request.description}
Generated by Claude gRPC Service
"""

def main():
    # TODO: Implement {request.description}
    pass

if __name__ == "__main__":
    main()
'''

        return ai_agent_pb2.GenerateCodeResponse(
            language=request.language,
            code=code,
            description=request.description,
            generated_at=datetime.now().isoformat(),
        )

    async def StreamPlan(
        self,
        request: ai_agent_pb2.PlanRequest,
        context: grpc.aio.ServicerContext,
    ):
        """스트리밍 계획 수립"""
        self.logger.info(f"StreamPlan: {request.task_description}")

        phases = ["Analysis", "Design", "Implementation", "Testing", "Review"]

        for i, phase in enumerate(phases):
            yield ai_agent_pb2.StreamMessage(
                stream_id=f"plan-{request.task_description[:10]}",
                type="progress",
                content=f"Phase {i + 1}: {phase}",
                progress_percent=(i + 1) / len(phases) * 100,
                timestamp=int(time.time() * 1000),
            )
            await asyncio.sleep(0.5)  # 시뮬레이션

        yield ai_agent_pb2.StreamMessage(
            stream_id=f"plan-{request.task_description[:10]}",
            type="result",
            content="Plan completed",
            progress_percent=100,
            timestamp=int(time.time() * 1000),
        )


class ClaudeGrpcService(GrpcBaseService):
    """Claude gRPC 서비스"""

    def __init__(self, host: str = "0.0.0.0", port: int = 5011):
        super().__init__(name="claude", host=host, port=port)

    def _register_services(self):
        """서비스 등록"""
        servicer = ClaudeGrpcServicer(self)
        ai_agent_pb2_grpc.add_ClaudeServiceServicer_to_server(servicer, self.server)


class GeminiGrpcServicer(ai_agent_pb2_grpc.GeminiServiceServicer):
    """Gemini gRPC 서비스 구현"""

    def __init__(self, service: "GeminiGrpcService"):
        self.service = service
        self.logger = service.logger

    async def HealthCheck(
        self,
        request: ai_agent_pb2.HealthCheckRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_agent_pb2.HealthCheckResponse:
        return ai_agent_pb2.HealthCheckResponse(
            status=ai_agent_pb2.HealthCheckResponse.ServingStatus.SERVING,
            version="1.0.0",
            uptime_seconds=self.service.get_uptime(),
        )

    async def Analyze(
        self,
        request: ai_agent_pb2.AnalyzeRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_agent_pb2.AnalyzeResponse:
        """분석"""
        self.logger.info(f"Analyze: {request.analysis_type}")

        findings = [
            ai_agent_pb2.AnalyzeResponse.Finding(
                category="structure",
                severity="info",
                description="Code structure analysis completed",
            ),
            ai_agent_pb2.AnalyzeResponse.Finding(
                category="patterns",
                severity="info",
                description="Design patterns identified",
            ),
        ]

        return ai_agent_pb2.AnalyzeResponse(
            analysis_type=request.analysis_type,
            content_length=len(request.content),
            token_estimate=len(request.content) // 4,
            findings=findings,
            summary=f"Analysis completed for {len(request.content)} chars",
            analyzed_at=datetime.now().isoformat(),
        )

    async def ReviewCode(
        self,
        request: ai_agent_pb2.ReviewCodeRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_agent_pb2.ReviewCodeResponse:
        """코드 리뷰"""
        self.logger.info(f"ReviewCode: {request.language}")

        issues = [
            ai_agent_pb2.ReviewCodeResponse.Issue(
                type="style",
                severity="low",
                line=1,
                message="Consider adding docstring",
                suggestion="Add module docstring",
            ),
        ]

        return ai_agent_pb2.ReviewCodeResponse(
            language=request.language,
            review_type=request.review_type,
            code_length=len(request.code),
            issues=issues,
            overall_score=95.0,
            reviewed_at=datetime.now().isoformat(),
        )


class GeminiGrpcService(GrpcBaseService):
    """Gemini gRPC 서비스"""

    def __init__(self, host: str = "0.0.0.0", port: int = 5012):
        super().__init__(name="gemini", host=host, port=port)

    def _register_services(self):
        servicer = GeminiGrpcServicer(self)
        ai_agent_pb2_grpc.add_GeminiServiceServicer_to_server(servicer, self.server)


class CodexGrpcServicer(ai_agent_pb2_grpc.CodexServiceServicer):
    """Codex gRPC 서비스 구현"""

    ALLOWED_COMMANDS = [
        "echo",
        "ls",
        "pwd",
        "date",
        "cat",
        "head",
        "tail",
        "wc",
        "grep",
        "find",
        "python",
        "pip",
        "npm",
        "node",
        "git",
        "make",
    ]

    def __init__(self, service: "CodexGrpcService"):
        self.service = service
        self.logger = service.logger

    async def HealthCheck(
        self,
        request: ai_agent_pb2.HealthCheckRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_agent_pb2.HealthCheckResponse:
        return ai_agent_pb2.HealthCheckResponse(
            status=ai_agent_pb2.HealthCheckResponse.ServingStatus.SERVING,
            version="1.0.0",
            uptime_seconds=self.service.get_uptime(),
        )

    async def Execute(
        self,
        request: ai_agent_pb2.ExecuteRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_agent_pb2.ExecuteResponse:
        """명령 실행"""
        self.logger.info(f"Execute: {request.command}")

        # 명령어 검증
        if not self._validate_command(request.command):
            return ai_agent_pb2.ExecuteResponse(
                success=False,
                command=request.command,
                exit_code=-1,
                stderr="Command not allowed",
            )

        # 명령 실행
        start_time = time.perf_counter()

        try:
            import os

            process = await asyncio.create_subprocess_shell(
                request.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=request.working_dir or os.getcwd(),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=request.timeout_seconds or 30,
            )

            duration = time.perf_counter() - start_time

            return ai_agent_pb2.ExecuteResponse(
                success=process.returncode == 0,
                command=request.command,
                exit_code=process.returncode,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                duration_seconds=round(duration, 3),
                executed_at=datetime.now().isoformat(),
            )

        except TimeoutError:
            return ai_agent_pb2.ExecuteResponse(
                success=False,
                command=request.command,
                exit_code=-1,
                stderr="Command timed out",
                executed_at=datetime.now().isoformat(),
            )

    def _validate_command(self, command: str) -> bool:
        """명령어 검증"""
        if not command:
            return False

        cmd_parts = command.strip().split()
        if not cmd_parts:
            return False

        import os

        base_cmd = os.path.basename(cmd_parts[0])

        return base_cmd in self.ALLOWED_COMMANDS

    async def StreamExecute(
        self,
        request: ai_agent_pb2.ExecuteRequest,
        context: grpc.aio.ServicerContext,
    ):
        """스트리밍 실행"""
        self.logger.info(f"StreamExecute: {request.command}")

        yield ai_agent_pb2.StreamMessage(
            stream_id=f"exec-{hash(request.command)}",
            type="log",
            content=f"Starting: {request.command}",
            timestamp=int(time.time() * 1000),
        )

        # 실제 실행
        result = await self.Execute(request, context)

        yield ai_agent_pb2.StreamMessage(
            stream_id=f"exec-{hash(request.command)}",
            type="result",
            content=result.stdout or result.stderr,
            progress_percent=100,
            timestamp=int(time.time() * 1000),
        )


class CodexGrpcService(GrpcBaseService):
    """Codex gRPC 서비스"""

    def __init__(self, host: str = "0.0.0.0", port: int = 5013):
        super().__init__(name="codex", host=host, port=port)

    def _register_services(self):
        servicer = CodexGrpcServicer(self)
        ai_agent_pb2_grpc.add_CodexServiceServicer_to_server(servicer, self.server)


# 서비스 실행 함수
async def run_claude_grpc():
    service = ClaudeGrpcService()
    await service.start()


async def run_gemini_grpc():
    service = GeminiGrpcService()
    await service.start()


async def run_codex_grpc():
    service = CodexGrpcService()
    await service.start()


if __name__ == "__main__":
    import sys

    service_name = sys.argv[1] if len(sys.argv) > 1 else "claude"

    services = {
        "claude": run_claude_grpc,
        "gemini": run_gemini_grpc,
        "codex": run_codex_grpc,
    }

    if service_name in services:
        asyncio.run(services[service_name]())
    else:
        print(f"Unknown service: {service_name}")
