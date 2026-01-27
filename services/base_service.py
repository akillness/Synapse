"""
베이스 서비스 클래스
"""
import asyncio
import contextlib
import logging
import signal
import sys
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from typing import Any

from .protocol import (
    ErrorCode,
    JsonRpcRequest,
    JsonRpcResponse,
    MessageFramer,
)

# 타입 별칭
MethodHandler = Callable[[dict[str, Any]], Any]


class ServiceProtocol:
    """서비스 프로토콜 인터페이스"""

    async def health(self) -> dict[str, Any]:
        raise NotImplementedError

    async def process(self, params: dict[str, Any]) -> Any:
        raise NotImplementedError


class BaseService(ABC):
    """비동기 TCP 서비스 베이스 클래스"""

    def __init__(
        self,
        name: str,
        host: str = "127.0.0.1",
        port: int = 5000,
        log_level: str = "INFO",
    ):
        self.name = name
        self.host = host
        self.port = port

        # 상태
        self.server: asyncio.Server | None = None
        self.start_time: datetime | None = None
        self.connections: set[asyncio.StreamWriter] = set()
        self._running = False

        # 메서드 핸들러 레지스트리
        self._handlers: dict[str, MethodHandler] = {}

        # 로깅 설정
        self.logger = logging.getLogger(f"service.{name}")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.logger.propagate = False  # 중복 로깅 방지

        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(name)-12s | %(levelname)-8s | %(message)s"
                )
            )
            self.logger.addHandler(handler)

        # 기본 핸들러 등록
        self._register_default_handlers()

    def _register_default_handlers(self):
        """기본 메서드 핸들러 등록"""
        self.register_handler("health", self._handle_health)
        self.register_handler("ping", self._handle_ping)
        self.register_handler("info", self._handle_info)

    def register_handler(self, method: str, handler: MethodHandler):
        """메서드 핸들러 등록"""
        self._handlers[method] = handler
        self.logger.debug(f"Registered handler: {method}")

    async def _handle_health(self, params: dict[str, Any]) -> dict[str, Any]:
        """헬스 체크 핸들러"""
        uptime = 0
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()

        return {
            "status": "healthy",
            "service": self.name,
            "host": self.host,
            "port": self.port,
            "uptime_seconds": int(uptime),
            "connections": len(self.connections),
            "timestamp": datetime.now().isoformat(),
        }

    async def _handle_ping(self, params: dict[str, Any]) -> dict[str, Any]:
        """핑 핸들러"""
        return {"pong": True, "timestamp": datetime.now().isoformat()}

    async def _handle_info(self, params: dict[str, Any]) -> dict[str, Any]:
        """서비스 정보 핸들러"""
        return {
            "name": self.name,
            "version": "1.0.0",
            "methods": list(self._handlers.keys()),
        }

    async def start(self):
        """서버 시작"""
        self._running = True
        self.start_time = datetime.now()

        self.server = await asyncio.start_server(
            self._handle_connection,
            self.host,
            self.port,
            reuse_address=True,
        )

        # 시그널 핸들러 설정
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        self._print_banner()

        async with self.server:
            await self.server.serve_forever()

    def _print_banner(self):
        """시작 배너 출력"""
        banner = f"""
╔══════════════════════════════════════════════════════════╗
║  {self.name.upper():^54}  ║
║  TCP Server Started                                      ║
║  Host: {self.host:<15} Port: {self.port:<22}  ║
║  Methods: {len(self._handlers):<46}  ║
╚══════════════════════════════════════════════════════════╝
"""
        self.logger.info(banner)

    async def stop(self):
        """서버 종료"""
        self.logger.info("Shutting down...")
        self._running = False

        # 모든 연결 종료
        for writer in list(self.connections):
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()

        if self.server:
            self.server.close()
            await self.server.wait_closed()

        self.logger.info("Server stopped")

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ):
        """클라이언트 연결 처리"""
        addr = writer.get_extra_info("peername")
        conn_id = f"{addr[0]}:{addr[1]}" if addr else "unknown"
        self.connections.add(writer)
        self.logger.info(f"Client connected: {conn_id}")

        try:
            while self._running:
                # 헤더 읽기 (4바이트)
                try:
                    header = await asyncio.wait_for(
                        reader.readexactly(MessageFramer.HEADER_SIZE),
                        timeout=300.0,  # 5분 타임아웃
                    )
                except TimeoutError:
                    self.logger.debug(f"Connection timeout: {conn_id}")
                    break

                msg_length = MessageFramer.decode_header(header)

                # 메시지 크기 검증
                if msg_length > MessageFramer.MAX_MESSAGE_SIZE:
                    self.logger.error(f"Message too large: {msg_length}")
                    await self._send_error(
                        writer, "", ErrorCode.INVALID_REQUEST, "Message too large"
                    )
                    continue

                # 페이로드 읽기
                payload = await reader.readexactly(msg_length)
                request_data = MessageFramer.decode_payload(payload)

                # 요청 처리
                request = JsonRpcRequest.from_dict(request_data)
                response = await self._process_request(request)

                # 응답 전송
                await self._send_response(writer, response)

        except asyncio.IncompleteReadError:
            self.logger.info(f"Client disconnected: {conn_id}")
        except ConnectionResetError:
            self.logger.info(f"Connection reset: {conn_id}")
        except Exception as e:
            self.logger.error(f"Error handling {conn_id}: {e}")
        finally:
            self.connections.discard(writer)
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
            self.logger.debug(f"Connection closed: {conn_id}")

    async def _process_request(self, request: JsonRpcRequest) -> JsonRpcResponse:
        """요청 처리"""
        self.logger.debug(f"Processing: {request.method} (id={request.id})")

        handler = self._handlers.get(request.method)
        if not handler:
            return JsonRpcResponse.create_error(
                request.id,
                ErrorCode.METHOD_NOT_FOUND,
                f"Method not found: {request.method}",
            )

        try:
            # 핸들러 호출
            result = handler(request.params)

            # 코루틴 처리
            if asyncio.iscoroutine(result):
                result = await result

            # 결과 검증
            if callable(result) and not isinstance(result, (dict, list, str, int, float, bool, type(None))):
                self.logger.warning(f"Handler returned callable: {type(result)}")
                result = {"error": "Handler returned invalid type"}

            response = JsonRpcResponse.success(request.id, result)
            return response

        except Exception as e:
            self.logger.error(f"Handler error: {e}", exc_info=True)
            return JsonRpcResponse.create_error(
                request.id,
                ErrorCode.INTERNAL_ERROR,
                str(e),
            )

    async def _send_response(
        self, writer: asyncio.StreamWriter, response: JsonRpcResponse
    ):
        """응답 전송"""
        try:
            # 타입 체크
            if not isinstance(response, JsonRpcResponse):
                self.logger.error(f"Invalid response type: {type(response)}")
                response = JsonRpcResponse.create_error(
                    "", ErrorCode.INTERNAL_ERROR, "Invalid response type"
                )

            response_dict = response.to_dict()
            data = MessageFramer.encode(response_dict)
            writer.write(data)
            await writer.drain()
        except Exception as e:
            self.logger.error(f"Failed to send response: {e}", exc_info=True)

    async def _send_error(
        self,
        writer: asyncio.StreamWriter,
        request_id: str,
        code: int,
        message: str,
    ):
        """에러 응답 전송"""
        response = JsonRpcResponse.create_error(request_id, code, message)
        await self._send_response(writer, response)

    @abstractmethod
    async def process(self, params: dict[str, Any]) -> Any:
        """서비스별 처리 로직 (서브클래스에서 구현)"""
        pass
