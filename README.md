# Synapse

[![CI](https://github.com/akillness/Synapse/actions/workflows/ci.yml/badge.svg)](https://github.com/akillness/Synapse/actions/workflows/ci.yml)
[![Docker](https://github.com/akillness/Synapse/actions/workflows/docker.yml/badge.svg)](https://github.com/akillness/Synapse/actions/workflows/docker.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![gRPC](https://img.shields.io/badge/gRPC-1.60+-green.svg)](https://grpc.io/)
[![uv](https://img.shields.io/badge/uv-monorepo-blueviolet.svg)](https://github.com/astral-sh/uv)

**Multi-Process AI Agent System** - A production-ready distributed AI agent orchestration framework with gRPC communication, resilience patterns, and comprehensive monitoring.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway                               │
│                    (FastAPI + Connection Pool)                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Load Balancer
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌───────────┐   ┌───────────┐   ┌───────────┐
    │  Claude   │   │  Gemini   │   │   Codex   │
    │ (5011)    │   │ (5012)    │   │  (5013)   │
    │Orchestrator│  │ Analyst   │   │ Executor  │
    └───────────┘   └───────────┘   └───────────┘
         │               │               │
         └───────────────┴───────────────┘
                    gRPC (HTTP/2 + Protobuf)
```

## Features

| Phase | Feature | Description |
|-------|---------|-------------|
| 1 | TCP Socket | JSON-RPC 2.0, asyncio, multi-process |
| 2 | gRPC | Protocol Buffers, streaming, compression |
| 3 | Resilience | Circuit Breaker, Retry, Timeout, Fallback |
| 4 | API Gateway | FastAPI, Connection Pool, Load Balancer |
| 5 | Deployment | Docker, Prometheus, Grafana |
| 6 | Testing | 201 unit tests, pytest, coverage |
| 7 | CI/CD | GitHub Actions, pre-commit |

### Resilience Patterns

- **Circuit Breaker**: CLOSED → OPEN → HALF_OPEN state machine
- **Retry**: Exponential backoff with jitter (gRPC standard)
- **Adaptive Timeout**: P95 response time based dynamic timeout
- **Fallback**: Cached responses + rule-based defaults
- **Streaming Checkpoint**: Resume interrupted streams

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Installation

```bash
git clone https://github.com/akillness/Synapse.git
cd Synapse

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e ".[dev]"
```

### Run Services

```bash
# Local development
python run_grpc_services.py --service all
uvicorn gateway.api_gateway:app --host 0.0.0.0 --port 8000

# Docker Compose (with monitoring)
docker-compose up -d
```

### Test

```bash
# Health check
curl http://localhost:8000/health

# Create plan
curl -X POST http://localhost:8000/api/v1/claude/plan \
  -H "Content-Type: application/json" \
  -d '{"task": "Build a REST API"}'
```

## API Reference

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Gateway health |
| GET | `/metrics` | Pool/LB metrics |
| POST | `/api/v1/claude/plan` | Create plan |
| POST | `/api/v1/claude/code` | Generate code |
| POST | `/api/v1/gemini/analyze` | Analyze content |
| POST | `/api/v1/gemini/review` | Review code |
| POST | `/api/v1/codex/execute` | Execute command |
| POST | `/api/v1/workflow` | Multi-agent workflow |

### gRPC Services

| Service | Port | Role |
|---------|------|------|
| Claude | 5011 | Orchestrator (planning, code generation) |
| Gemini | 5012 | Analyst (analysis, code review) |
| Codex | 5013 | Executor (command execution) |

## Project Structure

```
synapse/
├── .github/workflows/     # CI/CD pipelines
│   ├── ci.yml            # Test, lint, build
│   └── docker.yml        # Docker build & push
├── proto/                 # Protocol Buffers
├── services/              # gRPC services
│   ├── interceptors/      # Resilience patterns
│   └── grpc_generated/    # Generated code
├── clients/               # gRPC clients
├── gateway/               # API Gateway
├── tests/                 # 201 unit tests
├── monitoring/            # Prometheus & Grafana
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml         # uv monorepo config
└── .pre-commit-config.yaml
```

## Development

### Testing

```bash
# Run all tests
uv run pytest tests/ -v --ignore=tests/test_integration.py

# With coverage
uv run pytest --cov=services --cov=clients --cov=gateway
```

### Code Quality

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy services clients gateway
```

### Pre-commit

```bash
# Install hooks
uv run pre-commit install

# Run manually
uv run pre-commit run --all-files
```

## Configuration

### Resilience Config

```python
from clients.resilient_client import ResilienceConfig

config = ResilienceConfig(
    circuit_breaker_failure_threshold=3,
    circuit_breaker_reset_timeout=30.0,
    retry_max_attempts=4,
    retry_initial_backoff=1.0,
    adaptive_timeout_enabled=True,
    fallback_enabled=True,
)
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | INFO | Logging level |
| `CLAUDE_HOST` | 127.0.0.1 | Claude service host |
| `GEMINI_HOST` | 127.0.0.1 | Gemini service host |
| `CODEX_HOST` | 127.0.0.1 | Codex service host |

## Monitoring

| Service | URL | Credentials |
|---------|-----|-------------|
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | admin/synapse123 |
| Gateway | http://localhost:8000 | - |

## Performance

| Metric | Value |
|--------|-------|
| Average latency | 0.36ms |
| Min latency | 0.28ms |
| Max latency | 0.91ms |
| Throughput | ~2,700 req/s |

## CI/CD

### GitHub Actions

- **CI**: Lint (Ruff) → Test (pytest) → Build (uv)
- **Docker**: Build → Push to GHCR → Health check

### Triggers

- Push to `main`, `develop`
- Pull requests to `main`
- Tags `v*` (Docker release)

## License

MIT License - see [LICENSE](LICENSE) for details.
