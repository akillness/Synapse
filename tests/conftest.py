"""
Pytest Configuration and Shared Fixtures
Comprehensive Test Suite for Synaps AI Agent System
"""

import asyncio
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest
from grpc import StatusCode

# ============================================================================
# Async Event Loop Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Mock gRPC Components
# ============================================================================


@dataclass
class MockClientCallDetails:
    """Mock gRPC client call details."""

    method: str = "/test.Service/Method"
    timeout: float | None = None
    metadata: tuple | None = None
    credentials: Any | None = None
    wait_for_ready: bool | None = None


class MockAioRpcError(grpc.aio.AioRpcError):
    """Mock gRPC async RPC error for testing."""

    def __init__(self, code: StatusCode, details: str = "Mock error"):
        self._code = code
        self._details = details

    def code(self) -> StatusCode:
        return self._code

    def details(self) -> str:
        return self._details

    def __str__(self):
        return f"MockAioRpcError({self._code}, {self._details})"


@pytest.fixture
def mock_call_details():
    """Fixture for mock gRPC call details."""
    return MockClientCallDetails()


@pytest.fixture
def mock_grpc_error():
    """Factory fixture for creating mock gRPC errors."""

    def _create_error(code: StatusCode = StatusCode.UNAVAILABLE, details: str = "Mock error"):
        return MockAioRpcError(code, details)

    return _create_error


# ============================================================================
# Mock Continuation (gRPC Call Chain)
# ============================================================================


@pytest.fixture
def mock_success_continuation():
    """Continuation that always succeeds."""

    async def continuation(call_details, request):
        return {"status": "success", "data": "test"}

    return continuation


@pytest.fixture
def mock_failure_continuation():
    """Factory for continuation that fails with specific error."""

    def _create(error_code: StatusCode = StatusCode.UNAVAILABLE, fail_count: int = -1):
        call_count = 0

        async def continuation(call_details, request):
            nonlocal call_count
            call_count += 1

            if fail_count == -1 or call_count <= fail_count:
                raise MockAioRpcError(error_code)
            return {"status": "success", "data": "test"}

        return continuation

    return _create


@pytest.fixture
def mock_intermittent_continuation():
    """Continuation that fails intermittently."""

    def _create(fail_indices: list[int], error_code: StatusCode = StatusCode.UNAVAILABLE):
        call_count = 0

        async def continuation(call_details, request):
            nonlocal call_count
            call_count += 1

            if call_count in fail_indices:
                raise MockAioRpcError(error_code)
            return {"status": "success", "call_number": call_count}

        return continuation

    return _create


# ============================================================================
# Circuit Breaker Fixtures
# ============================================================================


@pytest.fixture
def circuit_breaker_config():
    """Default circuit breaker configuration for testing."""
    from services.interceptors.circuit_breaker import CircuitBreakerConfig

    return CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        reset_timeout=1.0,  # Short for testing
        half_open_max_calls=2,
    )


@pytest.fixture
def circuit_breaker(circuit_breaker_config):
    """Pre-configured circuit breaker instance."""
    from services.interceptors.circuit_breaker import CircuitBreaker

    return CircuitBreaker("test-service", circuit_breaker_config)


# ============================================================================
# Retry Policy Fixtures
# ============================================================================


@pytest.fixture
def retry_policy():
    """Default retry policy for testing."""
    from services.interceptors.retry import RetryPolicy

    return RetryPolicy(
        max_attempts=3,
        initial_backoff=0.01,  # Very short for testing
        max_backoff=0.1,
        backoff_multiplier=2.0,
        jitter=0.0,  # No jitter for deterministic testing
    )


@pytest.fixture
def retry_interceptor(retry_policy):
    """Pre-configured retry interceptor."""
    from services.interceptors.retry import RetryInterceptor

    return RetryInterceptor(retry_policy)


# ============================================================================
# Adaptive Timeout Fixtures
# ============================================================================


@pytest.fixture
def timeout_config():
    """Default timeout configuration for testing."""
    from services.interceptors.adaptive_timeout import TimeoutConfig

    return TimeoutConfig(
        default_timeout=5.0,
        min_timeout=1.0,
        max_timeout=30.0,
        adaptive_enabled=True,
        percentile=95.0,
        history_size=20,
        adjustment_factor=1.5,
    )


@pytest.fixture
def timeout_manager(timeout_config):
    """Pre-configured timeout manager."""
    from services.interceptors.adaptive_timeout import TimeoutManager

    return TimeoutManager(timeout_config)


# ============================================================================
# Fallback Fixtures
# ============================================================================


@pytest.fixture
def fallback_config():
    """Default fallback configuration for testing."""
    from services.fallback import FallbackConfig

    return FallbackConfig(
        cache_enabled=True,
        cache_ttl=60.0,
        max_cache_size=100,
        rule_based_enabled=True,
    )


@pytest.fixture
def fallback_manager(fallback_config):
    """Pre-configured fallback manager."""
    from services.fallback import FallbackManager

    return FallbackManager(fallback_config)


@pytest.fixture
def fallback_cache(fallback_config):
    """Pre-configured fallback cache."""
    from services.fallback import FallbackCache

    return FallbackCache(fallback_config)


# ============================================================================
# Streaming Checkpoint Fixtures
# ============================================================================


@pytest.fixture
def checkpoint_manager():
    """Pre-configured streaming checkpoint manager."""
    from services.streaming_checkpoint import StreamCheckpointManager

    return StreamCheckpointManager(
        checkpoint_interval=2,  # Checkpoint every 2 messages
        max_streams=10,
        ttl=60.0,
    )


@pytest.fixture
def mock_stream_factory():
    """Factory for creating mock async streams."""

    def _create(messages: list[Any]):
        async def stream():
            for msg in messages:
                yield msg

        return stream

    return _create


# ============================================================================
# Connection Pool Fixtures
# ============================================================================


@pytest.fixture
def pool_config():
    """Default connection pool configuration."""
    from gateway.connection_pool import PoolConfig

    return PoolConfig(
        min_size=2,
        max_size=5,
        max_idle_time=60.0,
        acquire_timeout=5.0,
        health_check_interval=30.0,
    )


@pytest.fixture
def mock_connection_factory():
    """Factory for creating mock connections."""
    connection_count = 0

    async def factory():
        nonlocal connection_count
        connection_count += 1
        conn = MagicMock()
        conn.id = connection_count
        conn.disconnect = AsyncMock()
        return conn

    return factory


@pytest.fixture
def mock_health_checker():
    """Mock health checker that always returns healthy."""

    async def checker(connection):
        return True

    return checker


# ============================================================================
# Load Balancer Fixtures
# ============================================================================


@pytest.fixture
def service_endpoints():
    """Pre-configured service endpoints for testing."""
    from gateway.load_balancer import ServiceEndpoint

    return [
        ServiceEndpoint(host="127.0.0.1", port=5001, weight=1),
        ServiceEndpoint(host="127.0.0.1", port=5002, weight=2),
        ServiceEndpoint(host="127.0.0.1", port=5003, weight=1),
    ]


# ============================================================================
# Mock gRPC Channel and Stubs
# ============================================================================


@pytest.fixture
def mock_grpc_channel():
    """Mock gRPC async channel."""
    channel = MagicMock()
    channel.close = AsyncMock()
    return channel


@pytest.fixture
def mock_claude_stub():
    """Mock Claude service stub."""
    stub = MagicMock()

    # Health check
    async def health_check(request):
        response = MagicMock()
        response.status = 1  # SERVING
        response.version = "1.0.0"
        response.uptime_seconds = 100
        return response

    # Create plan
    async def create_plan(request):
        response = MagicMock()
        response.task = request.task_description
        response.steps = []
        response.total_steps = 3
        response.estimated_agents = ["claude"]
        response.created_at = "2026-01-27T00:00:00Z"
        return response

    # Generate code
    async def generate_code(request):
        response = MagicMock()
        response.language = request.language
        response.code = "def hello(): pass"
        response.description = request.description
        response.generated_at = "2026-01-27T00:00:00Z"
        return response

    stub.HealthCheck = AsyncMock(side_effect=health_check)
    stub.CreatePlan = AsyncMock(side_effect=create_plan)
    stub.GenerateCode = AsyncMock(side_effect=generate_code)

    return stub


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_plan_request():
    """Sample plan request data."""
    return {
        "task": "Build a REST API",
        "constraints": ["Use Python", "Include tests", "Add documentation"],
    }


@pytest.fixture
def sample_code_request():
    """Sample code generation request data."""
    return {
        "description": "A function that calculates factorial",
        "language": "python",
    }


@pytest.fixture
def sample_analyze_request():
    """Sample analysis request data."""
    return {
        "content": "def foo(): return 42",
        "analysis_type": "code",
    }


@pytest.fixture
def sample_execute_request():
    """Sample execution request data."""
    return {
        "command": "echo 'Hello World'",
        "working_dir": "/tmp",
        "timeout": 30,
    }


# ============================================================================
# Time Manipulation Fixtures
# ============================================================================


@pytest.fixture
def mock_time():
    """Fixture for mocking time.time() for deterministic testing."""
    current_time = 1000.0

    def advance(seconds: float):
        nonlocal current_time
        current_time += seconds

    def get_time():
        return current_time

    with patch("time.time", side_effect=lambda: current_time):
        yield type("MockTime", (), {"advance": advance, "get_time": get_time})()


# ============================================================================
# Cleanup Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
async def cleanup_async():
    """Cleanup any lingering async resources after each test."""
    yield
    # Give a small window for cleanup
    await asyncio.sleep(0.01)
