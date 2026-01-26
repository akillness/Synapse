# Synapse

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![gRPC](https://img.shields.io/badge/gRPC-1.60+-green.svg)](https://grpc.io/)

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

### Phase 1: TCP Socket Communication
- JSON-RPC 2.0 protocol with 4-byte length prefix framing
- asyncio-based non-blocking I/O
- Multi-process service isolation

### Phase 2: gRPC Migration
- Protocol Buffers for type-safe serialization
- Server-side streaming for real-time updates
- gzip compression enabled

### Phase 3: Resilience Patterns
- **Circuit Breaker**: Prevents cascade failures (CLOSED → OPEN → HALF_OPEN)
- **Retry with Exponential Backoff**: Automatic retry with jitter
- **Adaptive Timeout**: Dynamic timeout based on response time history
- **Fallback Mechanism**: Cached responses and rule-based defaults
- **Streaming Checkpoint**: Resume interrupted streams

### Phase 4: API Gateway
- FastAPI-based unified entry point
- Connection pooling for efficient resource usage
- Multiple load balancing strategies (Round Robin, Weighted, Least Connections)

### Phase 5: Deployment
- Docker multi-stage builds
- docker-compose orchestration
- Prometheus + Grafana monitoring

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Docker & Docker Compose (optional)

### Installation

```bash
git clone https://github.com/yourusername/synapse.git
cd synapse

# Install with uv
uv sync

# Or with pip
pip install -e .
```

### Running Services

#### Local Development

```bash
# Start all gRPC services
python run_grpc_services.py --service all

# Start individual services
python run_grpc_services.py --service claude
python run_grpc_services.py --service gemini
python run_grpc_services.py --service codex

# Start API Gateway
uvicorn gateway.api_gateway:app --host 0.0.0.0 --port 8000
```

#### Docker Compose

```bash
# Start all services with monitoring
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Demo Client

```bash
# Run gRPC demo
python demo_grpc_client.py

# Test API Gateway
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/claude/plan \
  -H "Content-Type: application/json" \
  -d '{"task": "Build a REST API"}'
```

## API Reference

### Gateway Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Gateway health check |
| GET | `/metrics` | Pool and load balancer metrics |
| GET | `/api/v1/claude/health` | Claude service health |
| POST | `/api/v1/claude/plan` | Create execution plan |
| POST | `/api/v1/claude/code` | Generate code |
| GET | `/api/v1/gemini/health` | Gemini service health |
| POST | `/api/v1/gemini/analyze` | Analyze content |
| POST | `/api/v1/gemini/review` | Review code |
| GET | `/api/v1/codex/health` | Codex service health |
| POST | `/api/v1/codex/execute` | Execute command |
| POST | `/api/v1/workflow` | Run multi-agent workflow |

### gRPC Services

| Service | Port | Methods |
|---------|------|---------|
| Claude | 5011 | HealthCheck, CreatePlan, GenerateCode, StreamPlan |
| Gemini | 5012 | HealthCheck, Analyze, ReviewCode, StreamAnalyze |
| Codex | 5013 | HealthCheck, Execute, StreamExecute |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | INFO | Logging level |
| `CLAUDE_HOST` | 127.0.0.1 | Claude service host |
| `GEMINI_HOST` | 127.0.0.1 | Gemini service host |
| `CODEX_HOST` | 127.0.0.1 | Codex service host |

### Resilience Settings

```python
from clients.resilient_client import ResilienceConfig

config = ResilienceConfig(
    circuit_breaker_enabled=True,
    circuit_breaker_failure_threshold=3,
    circuit_breaker_reset_timeout=30.0,
    retry_enabled=True,
    retry_max_attempts=4,
    retry_initial_backoff=1.0,
    adaptive_timeout_enabled=True,
    fallback_enabled=True,
)
```

## Project Structure

```
synapse/
├── proto/                    # Protocol Buffer definitions
│   └── ai_agent.proto
├── services/                 # gRPC service implementations
│   ├── grpc_base_service.py
│   ├── grpc_generated/       # Generated protobuf code
│   └── interceptors/         # Resilience interceptors
│       ├── circuit_breaker.py
│       ├── retry.py
│       └── adaptive_timeout.py
├── clients/                  # gRPC clients
│   ├── grpc_client.py
│   └── resilient_client.py
├── gateway/                  # API Gateway
│   ├── api_gateway.py
│   ├── connection_pool.py
│   └── load_balancer.py
├── config/                   # Configuration
│   └── settings.py
├── tests/                    # Test suite
├── monitoring/               # Prometheus & Grafana configs
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Development

### Running Tests

```bash
pytest
pytest --cov=services --cov=clients --cov=gateway
pytest tests/test_integration.py -v
```

### Code Quality

```bash
ruff check .
ruff format .
mypy services clients gateway
```

### Proto Compilation

```bash
python -m grpc_tools.protoc \
  -I./proto \
  --python_out=./services/grpc_generated \
  --grpc_python_out=./services/grpc_generated \
  ./proto/ai_agent.proto
```

## Monitoring

Access monitoring dashboards:

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/synapse123)

## Performance

gRPC communication benchmarks:

| Metric | Value |
|--------|-------|
| Average latency | 0.36ms |
| Min latency | 0.28ms |
| Max latency | 0.91ms |
| Throughput | ~2,700 req/s |

## License

This project is licensed under the MIT License.
