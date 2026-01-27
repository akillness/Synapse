import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from clients.resilient_client import (
    ResilienceConfig,
    ResilientClaudeClient,
    ResilientClientConfig,
    ResilientCodexClient,
    ResilientGeminiClient,
    ResilientGrpcClient,
    create_resilient_client,
)


class TestResilienceConfig:
    def test_default_values(self):
        config = ResilienceConfig()

        assert config.circuit_breaker_enabled is True
        assert config.circuit_breaker_failure_threshold == 3
        assert config.circuit_breaker_reset_timeout == 30.0
        assert config.retry_enabled is True
        assert config.retry_max_attempts == 4
        assert config.adaptive_timeout_enabled is True
        assert config.fallback_enabled is True

    def test_custom_values(self):
        config = ResilienceConfig(
            circuit_breaker_failure_threshold=5,
            retry_max_attempts=2,
        )

        assert config.circuit_breaker_failure_threshold == 5
        assert config.retry_max_attempts == 2


class TestResilientClientConfig:
    def test_default_values(self):
        config = ResilientClientConfig()

        assert config.host == "127.0.0.1"
        assert config.port == 5011
        assert config.service_name == "unknown"
        assert config.compression is True
        assert isinstance(config.resilience, ResilienceConfig)

    def test_custom_values(self):
        config = ResilientClientConfig(
            host="localhost",
            port=8080,
            service_name="test-service",
        )

        assert config.host == "localhost"
        assert config.port == 8080
        assert config.service_name == "test-service"


class TestResilientGrpcClient:
    def test_address_property(self):
        config = ResilientClientConfig(host="127.0.0.1", port=5000)
        client = ResilientGrpcClient(config)

        assert client.address == "127.0.0.1:5000"

    def test_is_connected_initial_state(self):
        config = ResilientClientConfig()
        client = ResilientGrpcClient(config)

        assert client.is_connected is False

    def test_sets_up_circuit_breaker_when_enabled(self):
        config = ResilientClientConfig()
        config.resilience.circuit_breaker_enabled = True
        client = ResilientGrpcClient(config)

        assert client._circuit_breaker is not None

    def test_sets_up_timeout_manager_when_enabled(self):
        config = ResilientClientConfig()
        config.resilience.adaptive_timeout_enabled = True
        client = ResilientGrpcClient(config)

        assert client._timeout_manager is not None

    def test_sets_up_fallback_manager_when_enabled(self):
        config = ResilientClientConfig()
        config.resilience.fallback_enabled = True
        client = ResilientGrpcClient(config)

        assert client._fallback_manager is not None

    def test_no_circuit_breaker_when_disabled(self):
        config = ResilientClientConfig()
        config.resilience.circuit_breaker_enabled = False
        client = ResilientGrpcClient(config)

        assert client._circuit_breaker is None

    @pytest.mark.asyncio
    async def test_connect_creates_channel(self):
        config = ResilientClientConfig()
        client = ResilientGrpcClient(config)

        result = await client.connect()

        assert result is True
        assert client.is_connected is True
        assert client.channel is not None

        await client.disconnect()

    @pytest.mark.asyncio
    async def test_connect_returns_true_if_already_connected(self):
        config = ResilientClientConfig()
        client = ResilientGrpcClient(config)

        await client.connect()
        result = await client.connect()

        assert result is True

        await client.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_closes_channel(self):
        config = ResilientClientConfig()
        client = ResilientGrpcClient(config)

        await client.connect()
        await client.disconnect()

        assert client.is_connected is False
        assert client.channel is None

    @pytest.mark.asyncio
    async def test_session_context_manager(self):
        config = ResilientClientConfig()
        client = ResilientGrpcClient(config)

        async with client.session() as c:
            assert c.is_connected is True

        assert client.is_connected is False

    def test_get_metrics(self):
        config = ResilientClientConfig(service_name="test")
        client = ResilientGrpcClient(config)

        metrics = client.get_metrics()

        assert metrics["service"] == "test"
        assert metrics["connected"] is False
        assert "circuit_breaker" in metrics
        assert "timeout" in metrics
        assert "fallback_cache" in metrics


class TestResilientClaudeClient:
    def test_default_port(self):
        client = ResilientClaudeClient()

        assert client.config.port == 5011
        assert client.config.service_name == "claude"

    def test_custom_host_and_port(self):
        client = ResilientClaudeClient(host="localhost", port=9000)

        assert client.config.host == "localhost"
        assert client.config.port == 9000

    @pytest.mark.asyncio
    async def test_stub_property(self):
        client = ResilientClaudeClient()
        await client.connect()

        try:
            stub = client.stub
            assert stub is not None
        finally:
            await client.disconnect()


class TestResilientGeminiClient:
    def test_default_port(self):
        client = ResilientGeminiClient()

        assert client.config.port == 5012
        assert client.config.service_name == "gemini"

    @pytest.mark.asyncio
    async def test_stub_property(self):
        client = ResilientGeminiClient()
        await client.connect()

        try:
            stub = client.stub
            assert stub is not None
        finally:
            await client.disconnect()


class TestResilientCodexClient:
    def test_default_port(self):
        client = ResilientCodexClient()

        assert client.config.port == 5013
        assert client.config.service_name == "codex"

    @pytest.mark.asyncio
    async def test_stub_property(self):
        client = ResilientCodexClient()
        await client.connect()

        try:
            stub = client.stub
            assert stub is not None
        finally:
            await client.disconnect()


class TestCreateResilientClient:
    def test_creates_claude_client(self):
        client = create_resilient_client("claude")

        assert isinstance(client, ResilientClaudeClient)
        assert client.config.port == 5011

    def test_creates_gemini_client(self):
        client = create_resilient_client("gemini")

        assert isinstance(client, ResilientGeminiClient)
        assert client.config.port == 5012

    def test_creates_codex_client(self):
        client = create_resilient_client("codex")

        assert isinstance(client, ResilientCodexClient)
        assert client.config.port == 5013

    def test_raises_for_unknown_service(self):
        with pytest.raises(ValueError, match="Unknown service"):
            create_resilient_client("unknown")

    def test_accepts_custom_host(self):
        client = create_resilient_client("claude", host="localhost")

        assert client.config.host == "localhost"


class TestResilientClientInterceptors:
    def test_interceptors_added_for_all_enabled_features(self):
        config = ResilientClientConfig()
        config.resilience.circuit_breaker_enabled = True
        config.resilience.retry_enabled = True
        config.resilience.adaptive_timeout_enabled = True

        client = ResilientGrpcClient(config)

        assert len(client._interceptors) == 3

    def test_no_interceptors_when_all_disabled(self):
        config = ResilientClientConfig()
        config.resilience.circuit_breaker_enabled = False
        config.resilience.retry_enabled = False
        config.resilience.adaptive_timeout_enabled = False

        client = ResilientGrpcClient(config)

        assert len(client._interceptors) == 0


class TestResilientClientMetrics:
    @pytest.mark.asyncio
    async def test_metrics_include_circuit_breaker_state(self):
        client = ResilientClaudeClient()

        metrics = client.get_metrics()

        assert "circuit_breaker" in metrics
        assert "state" in metrics["circuit_breaker"]
        assert metrics["circuit_breaker"]["state"] == "closed"

    @pytest.mark.asyncio
    async def test_metrics_include_timeout_info(self):
        client = ResilientClaudeClient()

        metrics = client.get_metrics()

        assert "timeout" in metrics

    @pytest.mark.asyncio
    async def test_metrics_include_fallback_cache_stats(self):
        client = ResilientClaudeClient()

        metrics = client.get_metrics()

        assert "fallback_cache" in metrics
        assert "size" in metrics["fallback_cache"]
