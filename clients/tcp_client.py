"""
TCP 클라이언트 - 서비스 통신용
"""
import asyncio
import logging

# 상위 모듈 임포트를 위한 경로 설정
import sys
import uuid
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.protocol import (
    ErrorCode,
    JsonRpcRequest,
    JsonRpcResponse,
    MessageFramer,
)


@dataclass
class ConnectionConfig:
    """연결 설정"""
    host: str = "127.0.0.1"
    port: int = 5001
    timeout: float = 30.0
    retry_count: int = 3
    retry_delay: float = 1.0


class TcpClient:
    """비동기 TCP 클라이언트"""

    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._connected = False

        # 로깅
        self.logger = logging.getLogger(f"client:{config.host}:{config.port}")

    @property
    def is_connected(self) -> bool:
        return self._connected and self.writer is not None

    async def connect(self) -> bool:
        """서버 연결"""
        if self._connected:
            return True

        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.config.host, self.config.port),
                timeout=self.config.timeout,
            )
            self._connected = True
            self.logger.info(f"Connected to {self.config.host}:{self.config.port}")
            return True

        except TimeoutError:
            self.logger.error(f"Connection timeout: {self.config.host}:{self.config.port}")
            return False
        except ConnectionRefusedError:
            self.logger.error(f"Connection refused: {self.config.host}:{self.config.port}")
            return False
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False

    async def disconnect(self):
        """연결 종료"""
        if self.writer:
            self.writer.close()
            with suppress(Exception):
                await self.writer.wait_closed()
            self.writer = None
            self.reader = None
            self._connected = False
            self.logger.info("Disconnected")

    async def send_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> JsonRpcResponse:
        """요청 전송 및 응답 수신"""
        if not self._connected:
            raise ConnectionError("Not connected to server")

        request = JsonRpcRequest(method=method, params=params or {})
        timeout = timeout or self.config.timeout

        async with self._lock:
            try:
                # 요청 전송
                data = MessageFramer.encode(request.to_dict())
                self.writer.write(data)
                await self.writer.drain()

                # 응답 수신
                header = await asyncio.wait_for(
                    self.reader.readexactly(MessageFramer.HEADER_SIZE),
                    timeout=timeout,
                )
                msg_length = MessageFramer.decode_header(header)

                payload = await asyncio.wait_for(
                    self.reader.readexactly(msg_length),
                    timeout=timeout,
                )
                response_data = MessageFramer.decode_payload(payload)

                return JsonRpcResponse.from_dict(response_data)

            except TimeoutError:
                self.logger.error(f"Request timeout: {method}")
                return JsonRpcResponse.create_error(
                    request.id, ErrorCode.TIMEOUT, "Request timeout"
                )
            except Exception as e:
                self.logger.error(f"Request error: {e}")
                self._connected = False
                return JsonRpcResponse.create_error(
                    request.id, ErrorCode.INTERNAL_ERROR, str(e)
                )

    async def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        **kwargs,
    ) -> Any:
        """간편 호출 (결과만 반환)"""
        response = await self.send_request(method, params, **kwargs)

        if response.error:
            raise Exception(f"RPC Error [{response.error.code}]: {response.error.message}")

        return response.result

    @asynccontextmanager
    async def session(self):
        """컨텍스트 매니저로 연결 관리"""
        connected = await self.connect()
        if not connected:
            raise ConnectionError(f"Failed to connect to {self.config.host}:{self.config.port}")

        try:
            yield self
        finally:
            await self.disconnect()


class ServiceClient:
    """서비스별 클라이언트 팩토리"""

    # 서비스 포트 매핑
    SERVICE_PORTS = {
        "claude": 5001,
        "gemini": 5002,
        "codex": 5003,
    }

    def __init__(self, service_name: str, host: str = "127.0.0.1"):
        if service_name not in self.SERVICE_PORTS:
            raise ValueError(f"Unknown service: {service_name}")

        self.service_name = service_name
        self.config = ConnectionConfig(
            host=host,
            port=self.SERVICE_PORTS[service_name],
        )
        self.client = TcpClient(self.config)
        self.logger = logging.getLogger(f"service:{service_name}")

    async def connect(self) -> bool:
        return await self.client.connect()

    async def disconnect(self):
        await self.client.disconnect()

    @property
    def is_connected(self) -> bool:
        return self.client.is_connected

    # 공통 메서드
    async def health(self) -> dict[str, Any]:
        """헬스 체크"""
        return await self.client.call("health")

    async def ping(self) -> dict[str, Any]:
        """핑"""
        return await self.client.call("ping")

    async def info(self) -> dict[str, Any]:
        """서비스 정보"""
        return await self.client.call("info")

    async def process(self, task: str, content: str = "") -> dict[str, Any]:
        """범용 처리"""
        return await self.client.call("process", {"task": task, "content": content})

    @asynccontextmanager
    async def session(self):
        """세션 컨텍스트"""
        async with self.client.session():
            yield self


class ClaudeClient(ServiceClient):
    """Claude 서비스 전용 클라이언트"""

    def __init__(self, host: str = "127.0.0.1"):
        super().__init__("claude", host)

    async def plan(self, task: str, constraints: list = None) -> dict[str, Any]:
        """계획 수립"""
        return await self.client.call("plan", {
            "task": task,
            "constraints": constraints or [],
        })

    async def generate_code(
        self,
        description: str,
        language: str = "python",
        context: str = "",
    ) -> dict[str, Any]:
        """코드 생성"""
        return await self.client.call("generate_code", {
            "description": description,
            "language": language,
            "context": context,
        })

    async def orchestrate(
        self,
        workflow: list,
        context: dict = None,
    ) -> dict[str, Any]:
        """오케스트레이션"""
        return await self.client.call("orchestrate", {
            "workflow": workflow,
            "context": context or {},
            "workflow_id": str(uuid.uuid4()),
        })


class GeminiClient(ServiceClient):
    """Gemini 서비스 전용 클라이언트"""

    def __init__(self, host: str = "127.0.0.1"):
        super().__init__("gemini", host)

    async def analyze(
        self,
        content: str,
        analysis_type: str = "general",
        max_tokens: int = 100000,
    ) -> dict[str, Any]:
        """대용량 분석"""
        return await self.client.call("analyze", {
            "content": content,
            "type": analysis_type,
            "max_tokens": max_tokens,
        })

    async def research(
        self,
        query: str,
        sources: list = None,
        depth: str = "standard",
    ) -> dict[str, Any]:
        """리서치"""
        return await self.client.call("research", {
            "query": query,
            "sources": sources or [],
            "depth": depth,
        })

    async def review_code(
        self,
        code: str,
        language: str = "python",
        review_type: str = "comprehensive",
    ) -> dict[str, Any]:
        """코드 리뷰"""
        return await self.client.call("review_code", {
            "code": code,
            "language": language,
            "review_type": review_type,
        })


class CodexClient(ServiceClient):
    """Codex 서비스 전용 클라이언트"""

    def __init__(self, host: str = "127.0.0.1"):
        super().__init__("codex", host)

    async def execute(
        self,
        command: str,
        working_dir: str = None,
        timeout: int = 30,
        env: dict = None,
    ) -> dict[str, Any]:
        """명령 실행"""
        import os
        return await self.client.call("execute", {
            "command": command,
            "working_dir": working_dir or os.getcwd(),
            "timeout": timeout,
            "env": env or {},
        })

    async def build(
        self,
        project_dir: str,
        build_command: str = "make build",
        env: dict = None,
    ) -> dict[str, Any]:
        """빌드"""
        return await self.client.call("build", {
            "project_dir": project_dir,
            "build_command": build_command,
            "env": env or {},
        })

    async def test(
        self,
        project_dir: str,
        test_command: str = "pytest -v",
        coverage: bool = False,
    ) -> dict[str, Any]:
        """테스트 실행"""
        return await self.client.call("test", {
            "project_dir": project_dir,
            "test_command": test_command,
            "coverage": coverage,
        })

    async def deploy(
        self,
        target: str = "local",
        config: dict = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """배포"""
        return await self.client.call("deploy", {
            "target": target,
            "config": config or {},
            "dry_run": dry_run,
        })


# 편의 함수
def create_client(service_name: str, host: str = "127.0.0.1") -> ServiceClient:
    """서비스 클라이언트 생성"""
    clients = {
        "claude": ClaudeClient,
        "gemini": GeminiClient,
        "codex": CodexClient,
    }

    client_class = clients.get(service_name)
    if not client_class:
        raise ValueError(f"Unknown service: {service_name}")

    return client_class(host)
