"""
JSON-RPC 2.0 프로토콜 구현
"""
import json
import struct
import uuid
from dataclasses import asdict, dataclass, field
from enum import IntEnum
from typing import Any


class ErrorCode(IntEnum):
    """JSON-RPC 에러 코드"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    # 서버 정의 에러 (-32000 ~ -32099)
    SERVICE_UNAVAILABLE = -32000
    TIMEOUT = -32001
    CIRCUIT_OPEN = -32002


@dataclass
class JsonRpcRequest:
    """JSON-RPC 2.0 요청"""
    method: str
    params: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    jsonrpc: str = "2.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_bytes(self) -> bytes:
        return json.dumps(self.to_dict()).encode("utf-8")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JsonRpcRequest":
        return cls(
            method=data.get("method", ""),
            params=data.get("params", {}),
            id=data.get("id", str(uuid.uuid4())),
            jsonrpc=data.get("jsonrpc", "2.0"),
        )


@dataclass
class JsonRpcError:
    """JSON-RPC 에러"""
    code: int
    message: str
    data: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {"code": self.code, "message": self.message}
        if self.data is not None:
            result["data"] = self.data
        return result


@dataclass
class JsonRpcResponse:
    """JSON-RPC 2.0 응답"""
    id: str
    result: Any | None = None
    error: JsonRpcError | None = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> dict[str, Any]:
        response = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error:
            response["error"] = self.error.to_dict()
        else:
            response["result"] = self.result
        return response

    def to_bytes(self) -> bytes:
        return json.dumps(self.to_dict()).encode("utf-8")

    @classmethod
    def success(cls, id: str, result: Any) -> "JsonRpcResponse":
        return cls(id=id, result=result)

    @classmethod
    def create_error(
        cls, id: str, code: int, message: str, data: Any = None
    ) -> "JsonRpcResponse":
        """에러 응답 생성 (error 필드와 이름 충돌 방지)"""
        return cls(id=id, error=JsonRpcError(code, message, data))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JsonRpcResponse":
        error = None
        if "error" in data:
            err_data = data["error"]
            error = JsonRpcError(
                code=err_data.get("code", -32603),
                message=err_data.get("message", "Unknown error"),
                data=err_data.get("data"),
            )
        return cls(
            id=data.get("id", ""),
            result=data.get("result"),
            error=error,
            jsonrpc=data.get("jsonrpc", "2.0"),
        )


class MessageFramer:
    """메시지 프레이밍 (길이 접두사 방식)

    프레임 구조:
    ┌────────────────┬────────────────────────────────────┐
    │ Length (4B)    │           JSON Payload              │
    │ Big-endian     │    {"jsonrpc":"2.0",...}           │
    └────────────────┴────────────────────────────────────┘
    """

    HEADER_SIZE = 4
    MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10MB

    @staticmethod
    def encode(data: dict | bytes) -> bytes:
        """메시지 인코딩"""
        payload = json.dumps(data).encode("utf-8") if isinstance(data, dict) else data

        if len(payload) > MessageFramer.MAX_MESSAGE_SIZE:
            raise ValueError(f"Message too large: {len(payload)} bytes")

        length = struct.pack(">I", len(payload))
        return length + payload

    @staticmethod
    def decode_header(header: bytes) -> int:
        """헤더에서 메시지 길이 추출"""
        if len(header) != MessageFramer.HEADER_SIZE:
            raise ValueError(f"Invalid header size: {len(header)}")
        return struct.unpack(">I", header)[0]

    @staticmethod
    def decode_payload(payload: bytes) -> dict[str, Any]:
        """페이로드 디코딩"""
        return json.loads(payload.decode("utf-8"))
