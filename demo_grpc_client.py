#!/usr/bin/env python3
"""
gRPC 데모 클라이언트
Usage: python demo_grpc_client.py
"""
import asyncio
import json
import sys
from pathlib import Path

# 경로 설정
sys.path.insert(0, str(Path(__file__).parent))

from clients.grpc_client import (
    ClaudeGrpcClient,
    GeminiGrpcClient,
    CodexGrpcClient,
)


def print_result(title: str, result: dict):
    """결과 출력"""
    print(f"\n{'─' * 60}")
    print(f"│ {title}")
    print(f"{'─' * 60}")
    print(json.dumps(result, indent=2, ensure_ascii=False))


async def demo_claude():
    """Claude gRPC 서비스 데모"""
    print("\n" + "=" * 60)
    print("│ CLAUDE gRPC SERVICE DEMO")
    print("=" * 60)

    client = ClaudeGrpcClient()
    async with client.session():
        # 헬스 체크
        health = await client.health_check()
        print_result("Health Check", health)

        # 계획 수립
        plan = await client.create_plan(
            task="Build a REST API for user management",
            constraints=["Use Python FastAPI", "Include authentication"]
        )
        print_result("Plan Creation", plan)

        # 코드 생성
        code = await client.generate_code(
            description="User authentication middleware",
            language="python"
        )
        print_result("Code Generation", code)

        # 스트리밍 계획
        print(f"\n{'─' * 60}")
        print("│ Streaming Plan")
        print(f"{'─' * 60}")
        async for message in client.stream_plan("Build feature"):
            print(f"  [{message['type']}] {message['content']} ({message['progress_percent']:.0f}%)")


async def demo_gemini():
    """Gemini gRPC 서비스 데모"""
    print("\n" + "=" * 60)
    print("│ GEMINI gRPC SERVICE DEMO")
    print("=" * 60)

    client = GeminiGrpcClient()
    async with client.session():
        # 헬스 체크
        health = await client.health_check()
        print_result("Health Check", health)

        # 코드 분석
        sample_code = '''
def calculate_total(items):
    total = 0
    for item in items:
        total += item.price * item.quantity
    return total
'''
        analysis = await client.analyze(
            content=sample_code,
            analysis_type="code"
        )
        print_result("Code Analysis", analysis)

        # 코드 리뷰
        review = await client.review_code(
            code=sample_code,
            language="python"
        )
        print_result("Code Review", review)


async def demo_codex():
    """Codex gRPC 서비스 데모"""
    print("\n" + "=" * 60)
    print("│ CODEX gRPC SERVICE DEMO")
    print("=" * 60)

    client = CodexGrpcClient()
    async with client.session():
        # 헬스 체크
        health = await client.health_check()
        print_result("Health Check", health)

        # 명령 실행
        result = await client.execute(
            command="echo 'Hello from Codex gRPC!'",
            timeout=10
        )
        print_result("Execute: echo", result)

        # ls 명령
        ls_result = await client.execute(
            command="ls -la",
            timeout=10
        )
        print_result("Execute: ls -la", ls_result)

        # 스트리밍 실행
        print(f"\n{'─' * 60}")
        print("│ Streaming Execute")
        print(f"{'─' * 60}")
        async for message in client.stream_execute("date"):
            print(f"  [{message['type']}] {message['content']}")


async def demo_workflow():
    """멀티 에이전트 gRPC 워크플로우 데모"""
    print("\n" + "=" * 60)
    print("│ MULTI-AGENT gRPC WORKFLOW DEMO")
    print("=" * 60)

    claude = ClaudeGrpcClient()
    gemini = GeminiGrpcClient()
    codex = CodexGrpcClient()

    # 모든 서비스 연결
    await asyncio.gather(
        claude.connect(),
        gemini.connect(),
        codex.connect()
    )

    try:
        print("\n[Step 1] Claude gRPC: Creating plan...")
        plan = await claude.create_plan(task="Implement user login feature")
        print(f"  ✓ Plan created with {plan['total_steps']} steps")
        for step in plan['steps']:
            print(f"    {step['order']}. [{step['agent']}] {step['action']}")

        print("\n[Step 2] Gemini gRPC: Analyzing requirements...")
        analysis = await gemini.analyze(
            content="User login feature with JWT authentication",
            analysis_type="code"
        )
        print(f"  ✓ Analysis complete: {len(analysis['findings'])} findings")

        print("\n[Step 3] Claude gRPC: Generating code...")
        code = await claude.generate_code(
            description="JWT authentication handler",
            language="python"
        )
        print(f"  ✓ Code generated ({len(code['code'])} chars)")

        print("\n[Step 4] Gemini gRPC: Reviewing code...")
        review = await gemini.review_code(
            code=code['code'],
            language="python"
        )
        print(f"  ✓ Review score: {review['overall_score']}")

        print("\n[Step 5] Codex gRPC: Running tests...")
        result = await codex.execute(
            command="echo 'gRPC Tests passed!'",
            timeout=10
        )
        print(f"  ✓ Result: {result['stdout'].strip()}")

        print("\n" + "─" * 60)
        print("│ gRPC WORKFLOW COMPLETED SUCCESSFULLY!")
        print("─" * 60)

    finally:
        await asyncio.gather(
            claude.disconnect(),
            gemini.disconnect(),
            codex.disconnect()
        )


async def compare_tcp_vs_grpc():
    """TCP vs gRPC 성능 비교"""
    print("\n" + "=" * 60)
    print("│ TCP vs gRPC PERFORMANCE COMPARISON")
    print("=" * 60)

    import time

    # gRPC 테스트
    grpc_client = ClaudeGrpcClient()
    await grpc_client.connect()

    grpc_times = []
    for _ in range(10):
        start = time.perf_counter()
        await grpc_client.health_check()
        grpc_times.append((time.perf_counter() - start) * 1000)

    await grpc_client.disconnect()

    # TCP 테스트 (Phase 1 클라이언트가 있다면)
    try:
        from clients.tcp_client import ClaudeClient as TcpClaudeClient
        tcp_client = TcpClaudeClient()
        await tcp_client.connect()

        tcp_times = []
        for _ in range(10):
            start = time.perf_counter()
            await tcp_client.health()
            tcp_times.append((time.perf_counter() - start) * 1000)

        await tcp_client.disconnect()

        print(f"\n  TCP (JSON-RPC):")
        print(f"    Average: {sum(tcp_times)/len(tcp_times):.2f}ms")
        print(f"    Min: {min(tcp_times):.2f}ms")
        print(f"    Max: {max(tcp_times):.2f}ms")
    except Exception as e:
        print(f"\n  TCP: Not available ({e})")

    print(f"\n  gRPC (Protobuf):")
    print(f"    Average: {sum(grpc_times)/len(grpc_times):.2f}ms")
    print(f"    Min: {min(grpc_times):.2f}ms")
    print(f"    Max: {max(grpc_times):.2f}ms")


async def main():
    """메인 함수"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║   Multi-Process AI Agent System - gRPC Demo Client               ║
║   Phase 2: gRPC Communication (HTTP/2 + Protobuf)               ║
╚══════════════════════════════════════════════════════════════════╝
""")

    try:
        # 개별 서비스 데모
        await demo_claude()
        await demo_gemini()
        await demo_codex()

        # 워크플로우 데모
        await demo_workflow()

        # 성능 비교
        await compare_tcp_vs_grpc()

    except grpc.aio.AioRpcError as e:
        print(f"\n❌ gRPC Error: {e.code()} - {e.details()}")
        print("   Make sure gRPC services are running:")
        print("   python run_grpc_services.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    import grpc.aio
    asyncio.run(main())
