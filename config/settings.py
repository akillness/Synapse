"""
멀티프로세스 AI 시스템 - 설정
"""
import os
from dataclasses import dataclass


@dataclass
class ServiceConfig:
    """서비스 설정"""
    name: str
    host: str
    port: int


@dataclass
class Settings:
    """전역 설정"""
    # 서비스 포트 매핑
    SERVICES: dict[str, ServiceConfig] = None

    # 통신 설정
    MESSAGE_MAX_SIZE: int = 10 * 1024 * 1024  # 10MB
    CONNECTION_TIMEOUT: float = 30.0
    READ_TIMEOUT: float = 60.0

    # 재시도 설정
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0

    # Circuit Breaker 설정
    CIRCUIT_FAIL_MAX: int = 3
    CIRCUIT_RESET_TIMEOUT: int = 30

    # 로깅
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s | %(name)-12s | %(levelname)-8s | %(message)s"

    def __post_init__(self):
        if self.SERVICES is None:
            self.SERVICES = {
                "gateway": ServiceConfig("gateway", "127.0.0.1", 5000),
                "claude": ServiceConfig("claude", "127.0.0.1", 5001),
                "gemini": ServiceConfig("gemini", "127.0.0.1", 5002),
                "codex": ServiceConfig("codex", "127.0.0.1", 5003),
            }

    def get_service(self, name: str) -> ServiceConfig:
        """서비스 설정 조회"""
        return self.SERVICES.get(name)

    @classmethod
    def from_env(cls) -> "Settings":
        """환경변수에서 설정 로드"""
        settings = cls()
        settings.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        return settings


# 전역 설정 인스턴스
settings = Settings()
