import asyncio
import pytest
from unittest.mock import MagicMock

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.fallback import (
    FallbackConfig,
    FallbackCache,
    FallbackManager,
    RuleBasedFallback,
    ClaudeFallbackHandler,
    GeminiFallbackHandler,
    CodexFallbackHandler,
    CacheEntry,
    create_default_fallback_manager,
)


class TestCacheEntry:
    def test_is_not_expired_within_ttl(self):
        import time

        entry = CacheEntry(value="test", timestamp=time.time(), ttl=60.0)

        assert entry.is_expired is False

    def test_is_expired_after_ttl(self):
        import time

        entry = CacheEntry(value="test", timestamp=time.time() - 100, ttl=60.0)

        assert entry.is_expired is True


class TestFallbackCache:
    @pytest.mark.asyncio
    async def test_set_and_get(self, fallback_cache):
        await fallback_cache.set("method", {"key": "value"}, "response")

        result = await fallback_cache.get("method", {"key": "value"})

        assert result == "response"

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_entry(self, fallback_cache):
        result = await fallback_cache.get("missing", {})

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_expired_entry(self):
        config = FallbackConfig(cache_ttl=0.01)
        cache = FallbackCache(config)

        await cache.set("method", {}, "response")
        await asyncio.sleep(0.02)

        result = await cache.get("method", {})

        assert result is None

    @pytest.mark.asyncio
    async def test_evicts_oldest_when_full(self):
        config = FallbackConfig(max_cache_size=2)
        cache = FallbackCache(config)

        await cache.set("method1", {}, "response1")
        await asyncio.sleep(0.01)
        await cache.set("method2", {}, "response2")
        await asyncio.sleep(0.01)
        await cache.set("method3", {}, "response3")

        result1 = await cache.get("method1", {})
        result3 = await cache.get("method3", {})

        assert result1 is None
        assert result3 == "response3"

    @pytest.mark.asyncio
    async def test_clear_removes_all_entries(self, fallback_cache):
        await fallback_cache.set("method1", {}, "response1")
        await fallback_cache.set("method2", {}, "response2")

        await fallback_cache.clear()

        result1 = await fallback_cache.get("method1", {})
        result2 = await fallback_cache.get("method2", {})

        assert result1 is None
        assert result2 is None

    @pytest.mark.asyncio
    async def test_get_stats(self, fallback_cache):
        await fallback_cache.set("method", {}, "response")

        stats = fallback_cache.get_stats()

        assert stats["size"] == 1
        assert stats["max_size"] == fallback_cache.config.max_cache_size

    @pytest.mark.asyncio
    async def test_disabled_cache_does_not_store(self):
        config = FallbackConfig(cache_enabled=False)
        cache = FallbackCache(config)

        await cache.set("method", {}, "response")
        result = await cache.get("method", {})

        assert result is None


class TestRuleBasedFallback:
    @pytest.mark.asyncio
    async def test_register_and_use_rule(self):
        handler = RuleBasedFallback()
        handler.register_rule("Test", lambda req: {"fallback": True})

        result = await handler.handle("TestMethod", {})

        assert result == {"fallback": True}

    @pytest.mark.asyncio
    async def test_returns_none_for_no_matching_rule(self):
        handler = RuleBasedFallback()

        result = await handler.handle("UnknownMethod", {})

        assert result is None

    @pytest.mark.asyncio
    async def test_extracts_method_from_path(self):
        handler = RuleBasedFallback()
        handler.register_rule("Plan", lambda req: {"fallback": True})

        result = await handler.handle("/service/CreatePlan", {})

        assert result == {"fallback": True}

    @pytest.mark.asyncio
    async def test_async_rule_handler(self):
        handler = RuleBasedFallback()

        async def async_handler(req):
            return {"async_fallback": True}

        handler.register_rule("Test", async_handler)

        result = await handler.handle("TestMethod", {})

        assert result == {"async_fallback": True}

    @pytest.mark.asyncio
    async def test_handles_rule_exception(self):
        handler = RuleBasedFallback()

        def failing_handler(req):
            raise ValueError("Rule failed")

        handler.register_rule("Test", failing_handler)

        result = await handler.handle("TestMethod", {})

        assert result is None


class TestClaudeFallbackHandler:
    @pytest.mark.asyncio
    async def test_health_check_fallback(self):
        handler = ClaudeFallbackHandler()

        result = await handler.handle("HealthCheck", {})

        assert result["status"] == "DEGRADED"
        assert result["version"] == "fallback"

    @pytest.mark.asyncio
    async def test_create_plan_fallback(self):
        handler = ClaudeFallbackHandler()
        request = MagicMock()
        request.task_description = "Test task"

        result = await handler.handle("CreatePlan", request)

        assert result["task"] == "Test task"
        assert len(result["steps"]) == 1
        assert result["steps"][0]["phase"] == "Fallback"

    @pytest.mark.asyncio
    async def test_unknown_method_returns_none(self):
        handler = ClaudeFallbackHandler()

        result = await handler.handle("UnknownMethod", {})

        assert result is None


class TestGeminiFallbackHandler:
    @pytest.mark.asyncio
    async def test_health_check_fallback(self):
        handler = GeminiFallbackHandler()

        result = await handler.handle("HealthCheck", {})

        assert result["status"] == "DEGRADED"

    @pytest.mark.asyncio
    async def test_analyze_fallback(self):
        handler = GeminiFallbackHandler()
        request = MagicMock()
        request.analysis_type = "code"

        result = await handler.handle("Analyze", request)

        assert result["analysis_type"] == "code"
        assert result["findings"] == []
        assert "unavailable" in result["summary"].lower()


class TestCodexFallbackHandler:
    @pytest.mark.asyncio
    async def test_health_check_fallback(self):
        handler = CodexFallbackHandler()

        result = await handler.handle("HealthCheck", {})

        assert result["status"] == "DEGRADED"

    @pytest.mark.asyncio
    async def test_execute_fallback(self):
        handler = CodexFallbackHandler()
        request = MagicMock()
        request.command = "echo test"

        result = await handler.handle("Execute", request)

        assert result["success"] is False
        assert result["command"] == "echo test"
        assert result["exit_code"] == -1


class TestFallbackManager:
    @pytest.mark.asyncio
    async def test_get_fallback_from_cache(self, fallback_manager):
        await fallback_manager.cache_response("method", {}, "cached_response")

        result = await fallback_manager.get_fallback("service", "method", {})

        assert result == "cached_response"

    @pytest.mark.asyncio
    async def test_get_fallback_from_custom_handler(self, fallback_manager):
        class CustomHandler:
            async def handle(self, method, request):
                return {"custom": True}

        fallback_manager.register_handler("custom_service", CustomHandler())

        result = await fallback_manager.get_fallback("custom_service", "method", {})

        assert result == {"custom": True}

    @pytest.mark.asyncio
    async def test_get_fallback_from_rule(self, fallback_manager):
        fallback_manager.register_rule("Test", lambda req: {"rule": True})

        result = await fallback_manager.get_fallback("unknown", "TestMethod", {})

        assert result == {"rule": True}

    @pytest.mark.asyncio
    async def test_returns_none_when_no_fallback(self, fallback_manager):
        result = await fallback_manager.get_fallback("unknown", "unknown", {})

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_takes_priority(self, fallback_manager):
        fallback_manager.register_rule("Method", lambda req: {"rule": True})
        await fallback_manager.cache_response("Method", {}, "cached")

        result = await fallback_manager.get_fallback("service", "Method", {})

        assert result == "cached"


class TestDefaultFallbackManager:
    @pytest.mark.asyncio
    async def test_creates_manager_with_service_handlers(self):
        manager = create_default_fallback_manager()

        assert "claude" in manager._custom_handlers
        assert "gemini" in manager._custom_handlers
        assert "codex" in manager._custom_handlers

    @pytest.mark.asyncio
    async def test_claude_handler_works(self):
        manager = create_default_fallback_manager()

        result = await manager.get_fallback("claude", "HealthCheck", {})

        assert result["status"] == "DEGRADED"

    @pytest.mark.asyncio
    async def test_gemini_handler_works(self):
        manager = create_default_fallback_manager()

        result = await manager.get_fallback("gemini", "HealthCheck", {})

        assert result["status"] == "DEGRADED"

    @pytest.mark.asyncio
    async def test_codex_handler_works(self):
        manager = create_default_fallback_manager()

        result = await manager.get_fallback("codex", "HealthCheck", {})

        assert result["status"] == "DEGRADED"
