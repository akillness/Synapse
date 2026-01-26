# Multi-Process AI Agent System - Makefile

.PHONY: help install run-all run-claude run-gemini run-codex stop test demo clean

# 기본 목표
help:
	@echo "╔═══════════════════════════════════════════════════════════╗"
	@echo "║  Multi-Process AI Agent System - Phase 1                  ║"
	@echo "╠═══════════════════════════════════════════════════════════╣"
	@echo "║  Commands:                                                ║"
	@echo "║    make install     - Install dependencies                ║"
	@echo "║    make run-all     - Run all services                    ║"
	@echo "║    make run-claude  - Run Claude service only             ║"
	@echo "║    make run-gemini  - Run Gemini service only             ║"
	@echo "║    make run-codex   - Run Codex service only              ║"
	@echo "║    make stop        - Stop all services                   ║"
	@echo "║    make test        - Run integration tests               ║"
	@echo "║    make demo        - Run demo client                     ║"
	@echo "║    make clean       - Clean up cache files                ║"
	@echo "╚═══════════════════════════════════════════════════════════╝"

# 의존성 설치
install:
	pip install -r requirements.txt

# 모든 서비스 실행
run-all:
	python run_services.py --service all

# 개별 서비스 실행
run-claude:
	python run_services.py --service claude

run-gemini:
	python run_services.py --service gemini

run-codex:
	python run_services.py --service codex

# 서비스 중지
stop:
	@echo "Stopping services..."
	@pkill -f "run_services.py" 2>/dev/null || true
	@pkill -f "claude_service.py" 2>/dev/null || true
	@pkill -f "gemini_service.py" 2>/dev/null || true
	@pkill -f "codex_service.py" 2>/dev/null || true
	@echo "Services stopped"

# 테스트 실행
test:
	python -m pytest tests/ -v

# 빠른 테스트
quick-test:
	python tests/test_integration.py

# 데모 실행
demo:
	python demo_client.py

# 정리
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned up cache files"

# 상태 확인
status:
	@echo "Checking service ports..."
	@lsof -i :5001 2>/dev/null && echo "Claude (5001): Running" || echo "Claude (5001): Stopped"
	@lsof -i :5002 2>/dev/null && echo "Gemini (5002): Running" || echo "Gemini (5002): Stopped"
	@lsof -i :5003 2>/dev/null && echo "Codex (5003): Running" || echo "Codex (5003): Stopped"
