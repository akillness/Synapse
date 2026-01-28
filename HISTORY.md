# 멀티프로세스 AI 에이전트 시스템 - 개발 히스토리

> 모든 개발 과정, 결정, 이슈, 회고를 기록합니다.

---

## 프로젝트 개요

**목표**: Claude, Gemini, Codex를 독립적인 프로세스로 실행하고 포트 기반 통신으로 멀티에이전트 워크플로우 구현

**워크플로우 패턴**:
```
[Claude] 계획 수립 → [Gemini] 분석/리서치 → [Claude] 코드 작성 → [Codex] 실행/테스트
```

---

## 2026-01-27: Phase 1 - TCP 소켓 통신

### 구현
1. **protocol.py**: JSON-RPC 2.0 + MessageFramer
2. **base_service.py**: 비동기 TCP 서버 베이스
3. **claude_service.py**: Orchestrator (plan, generate_code)
4. **gemini_service.py**: Analyst (analyze, review_code, research)
5. **codex_service.py**: Executor (execute, validate_command)

### 해결된 이슈
- **Issue #1**: Port Already in Use → `lsof -ti:5001 | xargs kill -9`
- **Issue #2**: 메서드 이름 충돌 → `create_error()` 리네이밍
- **Issue #3**: 로그 중복 → `logger.propagate = False`

---

## 2026-01-27: Phase 2 - gRPC 전환

### 구현
1. **ai_agent.proto** (375 lines): 전체 서비스 인터페이스 정의
2. **grpc_base_service.py**: grpc.aio 기반 비동기 서버
3. **grpc_client.py**: session context manager 패턴

### 성능
```
gRPC: avg 0.36ms (min: 0.28ms, max: 0.91ms)
```

### 해결된 이슈
- **Issue #4**: Proto deprecated 옵션 → 제거
- **Issue #5**: gRPC import 에러 → 상대 import

---

## 2026-01-27: Phase 3 - Resilience

### 구현

#### Circuit Breaker (`services/interceptors/circuit_breaker.py`)
- 상태 머신: CLOSED → OPEN → HALF_OPEN
- System Error만 실패로 카운트 (UNAVAILABLE, DEADLINE_EXCEEDED)
- 설정: failure_threshold=3, reset_timeout=30s

#### Retry with Exponential Backoff (`services/interceptors/retry.py`)
- gRPC 표준 알고리즘 구현
- `current_backoff = min(initial * multiplier^attempt, max_backoff)`
- Jitter 적용으로 thundering herd 방지

#### Adaptive Timeout (`services/interceptors/adaptive_timeout.py`)
- 메서드별 기본 타임아웃 설정
- 응답 시간 히스토리 기반 P95 계산
- 동적 타임아웃 = P95 × adjustment_factor

#### Fallback (`services/fallback.py`)
- 캐시 응답 (TTL 기반)
- Rule-based 기본값
- 서비스별 커스텀 핸들러 (Claude, Gemini, Codex)

#### Streaming Checkpoint (`services/streaming_checkpoint.py`)
- 스트림 진행 상태 저장
- 중단 지점부터 재개
- ResumableStreamWrapper 제공

### Resilient Client (`clients/resilient_client.py`)
- 모든 interceptor 통합
- ResilienceConfig로 설정 관리
- get_metrics()로 상태 모니터링

---

## 2026-01-27: Phase 4 - API Gateway

### 구현

#### FastAPI Gateway (`gateway/api_gateway.py`)
- 통합 REST API 엔드포인트
- CORS 미들웨어
- 요청 타이밍 헤더 (`X-Response-Time`)
- 멀티에이전트 워크플로우 API

#### Connection Pool (`gateway/connection_pool.py`)
- Generic 타입 기반 범용 풀
- Health check 루프
- 자동 만료 및 제거
- 메트릭 수집

#### Load Balancer (`gateway/load_balancer.py`)
- Round Robin
- Weighted
- Least Connections
- Least Response Time

### API 엔드포인트
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Gateway 상태 |
| GET | `/metrics` | Pool/LB 메트릭 |
| POST | `/api/v1/claude/plan` | 계획 수립 |
| POST | `/api/v1/workflow` | 워크플로우 실행 |

---

## 2026-01-27: Phase 5 - Deployment

### 구현

#### Docker (`Dockerfile`)
- Multi-stage build (base → builder → runtime)
- Non-root user (synapse)
- uv 패키지 매니저 사용

#### docker-compose (`docker-compose.yml`)
- 6개 서비스: claude, gemini, codex, gateway, prometheus, grafana
- 네트워크 분리 (synapse-network)
- 볼륨 영속화

#### Monitoring
- Prometheus: 메트릭 수집
- Grafana: 대시보드 (admin/synapse123)

#### uv Monorepo (`pyproject.toml`)
- hatchling 빌드 백엔드
- ruff 린터/포매터
- pytest-asyncio 테스트

---

## 기술 스택 (최종)

| 구성요소 | 기술 |
|---------|------|
| 언어 | Python 3.11+ |
| 비동기 | asyncio |
| RPC | gRPC (HTTP/2 + Protobuf) |
| Gateway | FastAPI + Uvicorn |
| 패키지 관리 | uv |
| 컨테이너 | Docker + docker-compose |
| 모니터링 | Prometheus + Grafana |

---

## 서비스 포트 매핑 (최종)

| Service | Role | gRPC Port | HTTP Port |
|---------|------|-----------|-----------|
| Claude | Orchestrator | 5011 | - |
| Gemini | Analyst | 5012 | - |
| Codex | Executor | 5013 | - |
| Gateway | API Entry | - | 8000 |
| Prometheus | Metrics | - | 9090 |
| Grafana | Dashboard | - | 9300 |

---

## 회고

### 성과
1. **완전한 Resilience 스택**: Circuit Breaker, Retry, Timeout, Fallback, Checkpoint
2. **Production-Ready Gateway**: Connection Pool + Load Balancing
3. **컨테이너화 완료**: Docker + docker-compose + Monitoring
4. **Modern Python**: uv monorepo, ruff, pytest-asyncio

### 교훈
1. gRPC Interceptor 패턴이 비즈니스 로직 분리에 효과적
2. Generic 타입 기반 Connection Pool로 재사용성 확보
3. FastAPI lifespan context manager로 깔끔한 초기화/정리

### 개선 영역
1. 실제 LLM API 연동
2. mTLS 보안 적용
3. Kubernetes 배포
4. OpenTelemetry 트레이싱
