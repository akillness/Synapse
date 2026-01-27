#!/usr/bin/env python3
"""
모든 서비스 실행 스크립트
Usage: python run_services.py [--service SERVICE_NAME]
"""
import argparse
import asyncio
import logging
import multiprocessing
import sys
import time
from pathlib import Path

# 경로 설정
sys.path.insert(0, str(Path(__file__).parent))

import contextlib

from services.claude_service import ClaudeService
from services.codex_service import CodexService
from services.gemini_service import GeminiService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-12s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("launcher")


def run_service(service_class, **kwargs):
    """서비스 프로세스 실행 함수"""
    # 각 프로세스에서 새 이벤트 루프 생성
    service = service_class(**kwargs)
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(service.start())


def main():
    parser = argparse.ArgumentParser(description="AI Agent Service Launcher")
    parser.add_argument(
        "--service",
        choices=["claude", "gemini", "codex", "all"],
        default="all",
        help="Service to run (default: all)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind (default: 127.0.0.1)",
    )
    args = parser.parse_args()

    # 서비스 설정
    services = {
        "claude": (ClaudeService, {"host": args.host, "port": 5001}),
        "gemini": (GeminiService, {"host": args.host, "port": 5002}),
        "codex": (CodexService, {"host": args.host, "port": 5003}),
    }

    # spawn 방식 사용 (macOS/Windows 호환)
    multiprocessing.set_start_method("spawn", force=True)

    if args.service == "all":
        # 모든 서비스 실행
        print_banner()
        processes = []

        for name, (service_class, kwargs) in services.items():
            logger.info(f"Starting {name} service on port {kwargs['port']}...")
            process = multiprocessing.Process(
                target=run_service,
                args=(service_class,),
                kwargs=kwargs,
                name=name,
            )
            process.start()
            processes.append(process)
            time.sleep(0.5)  # 서비스 시작 간격

        logger.info("All services started!")
        logger.info("Press Ctrl+C to stop all services")

        # 종료 대기
        try:
            while True:
                time.sleep(1)
                # 프로세스 상태 확인
                for p in processes:
                    if not p.is_alive():
                        logger.warning(f"Service {p.name} stopped unexpectedly")

        except KeyboardInterrupt:
            logger.info("\nShutting down all services...")
            for p in processes:
                p.terminate()
                p.join(timeout=5)
            logger.info("All services stopped")

    else:
        # 단일 서비스 실행
        service_class, kwargs = services[args.service]
        logger.info(f"Starting {args.service} service...")
        run_service(service_class, **kwargs)


def print_banner():
    """시작 배너 출력"""
    banner = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   ███╗   ███╗██╗   ██╗██╗  ████████╗██╗      █████╗ ██╗          ║
║   ████╗ ████║██║   ██║██║  ╚══██╔══╝██║     ██╔══██╗██║          ║
║   ██╔████╔██║██║   ██║██║     ██║   ██║     ███████║██║          ║
║   ██║╚██╔╝██║██║   ██║██║     ██║   ██║     ██╔══██║██║          ║
║   ██║ ╚═╝ ██║╚██████╔╝███████╗██║   ██║     ██║  ██║██║          ║
║   ╚═╝     ╚═╝ ╚═════╝ ╚══════╝╚═╝   ╚═╝     ╚═╝  ╚═╝╚═╝          ║
║                                                                  ║
║   Multi-Process AI Agent System                                  ║
║   Phase 1: TCP Socket Communication                              ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║   Services:                                                      ║
║   • Claude  (Orchestrator) → Port 5001                          ║
║   • Gemini  (Analyst)      → Port 5002                          ║
║   • Codex   (Executor)     → Port 5003                          ║
╚══════════════════════════════════════════════════════════════════╝
"""
    print(banner)


if __name__ == "__main__":
    main()
