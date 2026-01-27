#!/usr/bin/env python3
"""
데모 클라이언트 - 모든 서비스 테스트
Usage: python demo_client.py
"""
import asyncio
import json
import sys
from pathlib import Path

# 경로 설정
sys.path.insert(0, str(Path(__file__).parent))

from clients.tcp_client import ClaudeClient, CodexClient, GeminiClient


def print_result(title: str, result: dict):
    """결과 출력"""
    print(f"\n{'─' * 60}")
    print(f"│ {title}")
    print(f"{'─' * 60}")
    print(json.dumps(result, indent=2, ensure_ascii=False))


async def demo_claude():
    """Claude 서비스 데모"""
    print("\n" + "=" * 60)
    print("│ CLAUDE SERVICE DEMO")
    print("=" * 60)

    client = ClaudeClient()
    async with client.session():
        # 헬스 체크
        health = await client.health()
        print_result("Health Check", health)

        # 계획 수립
        plan = await client.plan(
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


async def demo_gemini():
    """Gemini 서비스 데모"""
    print("\n" + "=" * 60)
    print("│ GEMINI SERVICE DEMO")
    print("=" * 60)

    client = GeminiClient()
    async with client.session():
        # 헬스 체크
        health = await client.health()
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
            language="python",
            review_type="comprehensive"
        )
        print_result("Code Review", review)


async def demo_codex():
    """Codex 서비스 데모"""
    print("\n" + "=" * 60)
    print("│ CODEX SERVICE DEMO")
    print("=" * 60)

    client = CodexClient()
    async with client.session():
        # 헬스 체크
        health = await client.health()
        print_result("Health Check", health)

        # 명령 실행
        result = await client.execute(
            command="echo 'Hello from Codex!'",
            timeout=10
        )
        print_result("Execute: echo", result)

        # 디렉토리 목록
        ls_result = await client.execute(
            command="ls -la",
            timeout=10
        )
        print_result("Execute: ls -la", ls_result)

        # 현재 날짜
        date_result = await client.execute(
            command="date",
            timeout=10
        )
        print_result("Execute: date", date_result)


async def demo_workflow():
    """멀티 에이전트 워크플로우 데모"""
    print("\n" + "=" * 60)
    print("│ MULTI-AGENT WORKFLOW DEMO")
    print("=" * 60)

    claude = ClaudeClient()
    gemini = GeminiClient()
    codex = CodexClient()

    # 모든 서비스 연결
    await asyncio.gather(
        claude.connect(),
        gemini.connect(),
        codex.connect()
    )

    try:
        print("\n[Step 1] Claude: Creating plan...")
        plan = await claude.plan(task="Implement user login feature")
        print(f"  ✓ Plan created with {plan['total_steps']} steps")
        for step in plan['steps']:
            print(f"    {step['order']}. [{step['agent']}] {step['action']}")

        print("\n[Step 2] Gemini: Analyzing requirements...")
        analysis = await gemini.analyze(
            content="User login feature with JWT authentication",
            analysis_type="code"
        )
        print(f"  ✓ Analysis complete: {len(analysis['findings'])} findings")

        print("\n[Step 3] Claude: Generating code...")
        code = await claude.generate_code(
            description="JWT authentication handler",
            language="python"
        )
        print(f"  ✓ Code generated ({len(code['code'])} chars)")

        print("\n[Step 4] Gemini: Reviewing code...")
        review = await gemini.review_code(
            code=code['code'],
            language="python"
        )
        print(f"  ✓ Review score: {review['overall_score']}")

        print("\n[Step 5] Codex: Running tests...")
        result = await codex.execute(
            command="echo 'Tests passed!'",
            timeout=10
        )
        print(f"  ✓ Result: {result['stdout'].strip()}")

        print("\n" + "─" * 60)
        print("│ WORKFLOW COMPLETED SUCCESSFULLY!")
        print("─" * 60)

    finally:
        await asyncio.gather(
            claude.disconnect(),
            gemini.disconnect(),
            codex.disconnect()
        )


async def main():
    """메인 함수"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║   Multi-Process AI Agent System - Demo Client                    ║
║   Phase 1: TCP Socket Communication                              ║
╚══════════════════════════════════════════════════════════════════╝
""")

    try:
        # 개별 서비스 데모
        await demo_claude()
        await demo_gemini()
        await demo_codex()

        # 워크플로우 데모
        await demo_workflow()

    except ConnectionRefusedError:
        print("\n❌ Error: Could not connect to services.")
        print("   Make sure all services are running:")
        print("   python run_services.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
