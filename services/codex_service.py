"""
Codex 서비스 - Executor 역할
명령 실행, 빌드, 배포, Docker/K8s 담당
"""

import asyncio
import os
from datetime import datetime
from typing import Any

from .base_service import BaseService


class CodexService(BaseService):
    """Codex AI 에이전트 서비스 (Executor)"""

    # 허용된 명령어 (보안)
    ALLOWED_COMMANDS = [
        "echo",
        "ls",
        "pwd",
        "date",
        "cat",
        "head",
        "tail",
        "wc",
        "grep",
        "find",
        "python",
        "pip",
        "npm",
        "node",
        "git",
        "make",
        "docker",
    ]

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5003,
        sandbox_mode: bool = True,
    ):
        super().__init__(
            name="codex",
            host=host,
            port=port,
        )
        self.sandbox_mode = sandbox_mode

        # 서비스별 핸들러 등록
        self.register_handler("process", self._handle_process)
        self.register_handler("execute", self._handle_execute)
        self.register_handler("build", self._handle_build)
        self.register_handler("test", self._handle_test)
        self.register_handler("deploy", self._handle_deploy)

    async def process(self, params: dict[str, Any]) -> Any:
        """범용 처리"""
        return await self._handle_process(params)

    async def _handle_process(self, params: dict[str, Any]) -> dict[str, Any]:
        """범용 처리 핸들러"""
        task = params.get("task", "")

        return {
            "output": f"[Codex] Executor ready for: {task}",
            "processed_at": datetime.now().isoformat(),
            "agent": "codex",
            "sandbox_mode": self.sandbox_mode,
        }

    async def _handle_execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """명령 실행 핸들러"""
        command = params.get("command", "")
        working_dir = params.get("working_dir", os.getcwd())
        timeout = params.get("timeout", 30)
        env = params.get("env", {})

        # 명령어 검증
        validation = self._validate_command(command)
        if not validation["allowed"]:
            return {
                "success": False,
                "error": validation["reason"],
                "exit_code": -1,
            }

        # 명령 실행
        result = await self._run_command(command, working_dir, timeout, env)

        return {
            "success": result["exit_code"] == 0,
            "command": command,
            "exit_code": result["exit_code"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "duration_seconds": result["duration"],
            "executed_at": datetime.now().isoformat(),
        }

    def _validate_command(self, command: str) -> dict[str, Any]:
        """명령어 유효성 검증"""
        if not command:
            return {"allowed": False, "reason": "Empty command"}

        if not self.sandbox_mode:
            return {"allowed": True, "reason": "Sandbox disabled"}

        # 첫 번째 단어 (명령어) 추출
        cmd_parts = command.strip().split()
        if not cmd_parts:
            return {"allowed": False, "reason": "Invalid command format"}

        base_cmd = cmd_parts[0]

        # 경로가 포함된 경우 파일명만 추출
        if "/" in base_cmd:
            base_cmd = os.path.basename(base_cmd)

        # 허용된 명령어인지 확인
        if base_cmd not in self.ALLOWED_COMMANDS:
            return {
                "allowed": False,
                "reason": f"Command not allowed: {base_cmd}. Allowed: {', '.join(self.ALLOWED_COMMANDS)}",
            }

        # 위험한 패턴 검사
        dangerous_patterns = [
            "rm -rf",
            "sudo",
            "> /",
            "| rm",
            "&& rm",
            "; rm",
            "mkfs",
            "dd if=",
            ":(){",  # fork bomb
        ]

        for pattern in dangerous_patterns:
            if pattern in command.lower():
                return {"allowed": False, "reason": f"Dangerous pattern detected: {pattern}"}

        return {"allowed": True, "reason": "Command validated"}

    async def _run_command(
        self,
        command: str,
        working_dir: str,
        timeout: int,
        env: dict[str, str],
    ) -> dict[str, Any]:
        """명령 실행"""
        import time

        start_time = time.perf_counter()

        # 환경 변수 설정
        process_env = os.environ.copy()
        process_env.update(env)

        try:
            # 비동기로 프로세스 실행
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=process_env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
                exit_code = process.returncode

            except TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Command timed out after {timeout} seconds",
                    "duration": timeout,
                }

            duration = time.perf_counter() - start_time

            return {
                "exit_code": exit_code,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "duration": round(duration, 3),
            }

        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "duration": time.perf_counter() - start_time,
            }

    async def _handle_build(self, params: dict[str, Any]) -> dict[str, Any]:
        """빌드 핸들러"""
        project_dir = params.get("project_dir", os.getcwd())
        build_command = params.get("build_command", "make build")
        env = params.get("env", {})

        # 빌드 실행
        result = await self._run_command(build_command, project_dir, 300, env)

        return {
            "success": result["exit_code"] == 0,
            "project_dir": project_dir,
            "build_command": build_command,
            "exit_code": result["exit_code"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "duration_seconds": result["duration"],
            "built_at": datetime.now().isoformat(),
        }

    async def _handle_test(self, params: dict[str, Any]) -> dict[str, Any]:
        """테스트 실행 핸들러"""
        project_dir = params.get("project_dir", os.getcwd())
        test_command = params.get("test_command", "pytest -v")
        coverage = params.get("coverage", False)

        if coverage:
            test_command = "pytest --cov=. --cov-report=term-missing -v"

        # 테스트 실행
        result = await self._run_command(test_command, project_dir, 600, {})

        # 결과 파싱 (시뮬레이션)
        test_results = self._parse_test_output(result["stdout"])

        return {
            "success": result["exit_code"] == 0,
            "project_dir": project_dir,
            "test_command": test_command,
            "exit_code": result["exit_code"],
            "output": result["stdout"],
            "errors": result["stderr"],
            "test_results": test_results,
            "duration_seconds": result["duration"],
            "tested_at": datetime.now().isoformat(),
        }

    def _parse_test_output(self, output: str) -> dict[str, Any]:
        """테스트 출력 파싱"""
        # 간단한 파싱 (실제로는 더 정교한 파싱 필요)
        return {
            "passed": output.count("PASSED") if "PASSED" in output else 0,
            "failed": output.count("FAILED") if "FAILED" in output else 0,
            "skipped": output.count("SKIPPED") if "SKIPPED" in output else 0,
        }

    async def _handle_deploy(self, params: dict[str, Any]) -> dict[str, Any]:
        """배포 핸들러"""
        target = params.get("target", "local")
        params.get("config", {})
        dry_run = params.get("dry_run", True)

        # 배포 시뮬레이션 (실제로는 더 복잡한 로직)
        if dry_run:
            return {
                "success": True,
                "target": target,
                "dry_run": True,
                "message": "Dry run completed successfully",
                "steps": [
                    "1. Validate configuration",
                    "2. Build artifacts",
                    "3. Push to registry",
                    "4. Deploy to target",
                    "5. Health check",
                ],
                "deployed_at": datetime.now().isoformat(),
            }

        return {
            "success": True,
            "target": target,
            "dry_run": False,
            "message": "Deployment initiated (simulated)",
            "deployed_at": datetime.now().isoformat(),
        }


async def main():
    """Codex 서비스 실행"""
    service = CodexService()
    await service.start()


if __name__ == "__main__":
    asyncio.run(main())
