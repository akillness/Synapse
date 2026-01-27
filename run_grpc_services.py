#!/usr/bin/env python3
"""
gRPC 서비스 런처
Usage: python run_grpc_services.py [--service SERVICE_NAME]
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

from services.grpc_base_service import (
    ClaudeGrpcService,
    CodexGrpcService,
    GeminiGrpcService,
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("grpc.launcher")


def run_service(service_class, **kwargs):
    """서비스 프로세스 실행"""
    service = service_class(**kwargs)
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(service.start())


def main():
    parser = argparse.ArgumentParser(description="gRPC AI Agent Service Launcher")
    parser.add_argument(
        "--service",
        choices=["claude", "gemini", "codex", "all"],
        default="all",
        help="Service to run (default: all)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind (default: 0.0.0.0)",
    )
    args = parser.parse_args()

    # gRPC 서비스 포트 (TCP 포트와 분리)
    services = {
        "claude": (ClaudeGrpcService, {"host": args.host, "port": 5011}),
        "gemini": (GeminiGrpcService, {"host": args.host, "port": 5012}),
        "codex": (CodexGrpcService, {"host": args.host, "port": 5013}),
    }

    # spawn 방식
    multiprocessing.set_start_method("spawn", force=True)

    if args.service == "all":
        print_banner()
        processes = []

        for name, (service_class, kwargs) in services.items():
            logger.info(f"Starting gRPC {name} service on port {kwargs['port']}...")
            process = multiprocessing.Process(
                target=run_service,
                args=(service_class,),
                kwargs=kwargs,
                name=f"grpc-{name}",
            )
            process.start()
            processes.append(process)
            time.sleep(0.5)

        logger.info("All gRPC services started!")
        logger.info("Press Ctrl+C to stop all services")

        try:
            while True:
                time.sleep(1)
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
        service_class, kwargs = services[args.service]
        logger.info(f"Starting gRPC {args.service} service...")
        run_service(service_class, **kwargs)


def print_banner():
    banner = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║    ██████╗ ██████╗ ██████╗  ██████╗                             ║
║   ██╔════╝ ██╔══██╗██╔══██╗██╔════╝                             ║
║   ██║  ███╗██████╔╝██████╔╝██║                                  ║
║   ██║   ██║██╔══██╗██╔═══╝ ██║                                  ║
║   ╚██████╔╝██║  ██║██║     ╚██████╗                             ║
║    ╚═════╝ ╚═╝  ╚═╝╚═╝      ╚═════╝                             ║
║                                                                  ║
║   Multi-Process AI Agent System                                  ║
║   Phase 2: gRPC Communication (HTTP/2 + Protobuf)               ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║   gRPC Services:                                                 ║
║   • Claude  (Orchestrator) → Port 5011                          ║
║   • Gemini  (Analyst)      → Port 5012                          ║
║   • Codex   (Executor)     → Port 5013                          ║
║                                                                  ║
║   TCP Services (Phase 1):                                        ║
║   • Claude → 5001 | Gemini → 5002 | Codex → 5003                ║
╚══════════════════════════════════════════════════════════════════╝
"""
    print(banner)


if __name__ == "__main__":
    main()
