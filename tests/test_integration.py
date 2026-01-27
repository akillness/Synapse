"""
Phase 1 통합 테스트
서비스들이 실행 중인 상태에서 테스트 실행:
  python -m pytest tests/test_integration.py -v
"""

import asyncio
import sys
from pathlib import Path

import pytest

# 경로 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

from clients.tcp_client import (
    ClaudeClient,
    CodexClient,
    ConnectionConfig,
    GeminiClient,
    TcpClient,
)


# pytest-asyncio 설정
@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class TestClaudeService:
    """Claude 서비스 테스트"""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """헬스 체크 테스트"""
        client = ClaudeClient()
        async with client.session():
            result = await client.health()

            assert result["status"] == "healthy"
            assert result["service"] == "claude"
            assert "uptime_seconds" in result

    @pytest.mark.asyncio
    async def test_ping(self):
        """핑 테스트"""
        client = ClaudeClient()
        async with client.session():
            result = await client.ping()

            assert result["pong"] is True
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_info(self):
        """서비스 정보 테스트"""
        client = ClaudeClient()
        async with client.session():
            result = await client.info()

            assert result["name"] == "claude"
            assert "methods" in result
            assert "health" in result["methods"]

    @pytest.mark.asyncio
    async def test_process(self):
        """범용 처리 테스트"""
        client = ClaudeClient()
        async with client.session():
            result = await client.process(task="Test task", content="Test content")

            assert "output" in result
            assert result["agent"] == "claude"

    @pytest.mark.asyncio
    async def test_plan(self):
        """계획 수립 테스트"""
        client = ClaudeClient()
        async with client.session():
            result = await client.plan(
                task="Build a REST API", constraints=["Use Python", "Include tests"]
            )

            assert "steps" in result
            assert len(result["steps"]) > 0
            assert "total_steps" in result

    @pytest.mark.asyncio
    async def test_generate_code(self):
        """코드 생성 테스트"""
        client = ClaudeClient()
        async with client.session():
            result = await client.generate_code(
                description="Hello world function", language="python"
            )

            assert "code" in result
            assert result["language"] == "python"


class TestGeminiService:
    """Gemini 서비스 테스트"""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """헬스 체크 테스트"""
        client = GeminiClient()
        async with client.session():
            result = await client.health()

            assert result["status"] == "healthy"
            assert result["service"] == "gemini"

    @pytest.mark.asyncio
    async def test_analyze(self):
        """분석 테스트"""
        client = GeminiClient()
        async with client.session():
            result = await client.analyze(
                content="def hello(): return 'world'", analysis_type="code"
            )

            assert "findings" in result
            assert "summary" in result

    @pytest.mark.asyncio
    async def test_research(self):
        """리서치 테스트"""
        client = GeminiClient()
        async with client.session():
            result = await client.research(query="Python async programming", depth="standard")

            assert "results" in result
            assert "query" in result

    @pytest.mark.asyncio
    async def test_review_code(self):
        """코드 리뷰 테스트"""
        client = GeminiClient()
        async with client.session():
            result = await client.review_code(code="def foo(): pass", language="python")

            assert "issues" in result
            assert "overall_score" in result


class TestCodexService:
    """Codex 서비스 테스트"""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """헬스 체크 테스트"""
        client = CodexClient()
        async with client.session():
            result = await client.health()

            assert result["status"] == "healthy"
            assert result["service"] == "codex"

    @pytest.mark.asyncio
    async def test_execute_allowed(self):
        """허용된 명령 실행 테스트"""
        client = CodexClient()
        async with client.session():
            result = await client.execute(command="echo Hello World", timeout=10)

            assert result["success"] is True
            assert "Hello World" in result["stdout"]

    @pytest.mark.asyncio
    async def test_execute_ls(self):
        """ls 명령 테스트"""
        client = CodexClient()
        async with client.session():
            result = await client.execute(command="ls -la", timeout=10)

            assert result["success"] is True
            assert result["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_execute_blocked(self):
        """차단된 명령 테스트"""
        client = CodexClient()
        async with client.session():
            result = await client.execute(command="sudo rm -rf /", timeout=10)

            assert result["success"] is False
            assert (
                "not allowed" in result["error"].lower() or "dangerous" in result["error"].lower()
            )


class TestMultiServiceWorkflow:
    """멀티 서비스 워크플로우 테스트"""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """전체 워크플로우 테스트"""
        claude = ClaudeClient()
        gemini = GeminiClient()
        codex = CodexClient()

        # 모든 서비스 연결
        await asyncio.gather(claude.connect(), gemini.connect(), codex.connect())

        try:
            # 1. Claude: 계획 수립
            plan = await claude.plan(task="Build a feature")
            assert len(plan["steps"]) > 0
            print(f"✓ Plan created with {plan['total_steps']} steps")

            # 2. Gemini: 분석
            analysis = await gemini.analyze(content="sample code content", analysis_type="code")
            assert "findings" in analysis
            print(f"✓ Analysis completed with {len(analysis['findings'])} findings")

            # 3. Codex: 실행
            execution = await codex.execute(command="echo 'Build complete'")
            assert execution["success"]
            print(f"✓ Execution completed: {execution['stdout'].strip()}")

        finally:
            await asyncio.gather(claude.disconnect(), gemini.disconnect(), codex.disconnect())

    @pytest.mark.asyncio
    async def test_parallel_requests(self):
        """병렬 요청 테스트"""
        clients = [ClaudeClient(), GeminiClient(), CodexClient()]

        # 모든 서비스 연결
        for client in clients:
            await client.connect()

        try:
            # 병렬로 헬스 체크
            results = await asyncio.gather(
                clients[0].health(), clients[1].health(), clients[2].health()
            )

            assert all(r["status"] == "healthy" for r in results)
            services = [r["service"] for r in results]
            assert set(services) == {"claude", "gemini", "codex"}

        finally:
            for client in clients:
                await client.disconnect()


class TestConnectionHandling:
    """연결 처리 테스트"""

    @pytest.mark.asyncio
    async def test_reconnect(self):
        """재연결 테스트"""
        client = ClaudeClient()

        # 첫 연결
        assert await client.connect()
        result1 = await client.health()
        await client.disconnect()

        # 재연결
        assert await client.connect()
        result2 = await client.health()
        await client.disconnect()

        assert result1["status"] == result2["status"]

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """컨텍스트 매니저 테스트"""
        async with ClaudeClient().session() as client:
            result = await client.health()
            assert result["status"] == "healthy"

        # 세션 종료 후 연결 확인
        assert not client.is_connected

    @pytest.mark.asyncio
    async def test_connection_refused(self):
        """연결 거부 테스트"""
        config = ConnectionConfig(host="127.0.0.1", port=59999)  # 존재하지 않는 포트
        client = TcpClient(config)

        connected = await client.connect()
        assert connected is False


# 직접 실행용
async def run_quick_test():
    """빠른 테스트 실행"""
    print("=" * 60)
    print("Phase 1 Quick Test")
    print("=" * 60)

    services = [
        ("claude", ClaudeClient),
        ("gemini", GeminiClient),
        ("codex", CodexClient),
    ]

    for name, client_class in services:
        print(f"\nTesting {name}...")
        client = client_class()

        try:
            await client.connect()
            health = await client.health()
            print(f"  ✓ {name}: {health['status']}")

            # 서비스별 추가 테스트
            if name == "claude":
                plan = await client.plan("Test task")
                print(f"  ✓ Plan created: {plan['total_steps']} steps")
            elif name == "gemini":
                analysis = await client.analyze("test code")
                print(f"  ✓ Analysis: {len(analysis['findings'])} findings")
            elif name == "codex":
                result = await client.execute("echo test")
                print(f"  ✓ Execute: {result['stdout'].strip()}")

        except Exception as e:
            print(f"  ✗ {name}: {e}")
        finally:
            await client.disconnect()

    print("\n" + "=" * 60)
    print("Quick test completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_quick_test())
