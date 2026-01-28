# Synapse Multi-AI Agent Orchestration Improvements

## TL;DR

> **Quick Summary**: Enhance Synapse with workflow orchestration patterns (pipeline/parallel/swarm), real-time SSE streaming, Redis-backed caching, structured error handling, and native MCP tool integration for seamless AI agent access.
> 
> **Deliverables**:
> - Enhanced `/api/v1/workflow` endpoint with 3 workflow types
> - SSE streaming endpoints (`/stream` variants)
> - Structured error responses with retry guidance
> - Redis caching layer (replacing in-memory)
> - MCP server exposing 5 Synapse tools
> - SKILL.md with quick commands and auto-detection
> 
> **Estimated Effort**: Large (6 feature areas, ~15-20 tasks)
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 (deps setup) → Task 2 (Redis) → Tasks 3-6 (parallel) → Task 7-8 (integration)

---

## Context

### Original Request
User requested 6 improvements to Synapse multi-AI agent orchestration system:
1. Workflow endpoint enhancement with pipeline/parallel/swarm types
2. SSE streaming response support
3. Enhanced error handling with retry_after and fallback info
4. Redis caching layer to replace in-memory FallbackCache
5. MCP tool integration for native AI agent access
6. SKILL.md improvements with quick commands

### Interview Summary
**Key Discussions**:
- **Redis deployment**: Add to docker-compose.yml as managed service
- **MCP transport**: stdio (works with Claude Desktop and OpenCode)
- **Backward compatibility**: Yes, `workflow_type` defaults to 'pipeline'
- **Test strategy**: TDD - write tests first, ensure coverage

**Research Findings**:
- Gateway uses FastAPI with lifespan management, hardcoded sequential workflow in `/api/v1/workflow`
- gRPC services: Claude (5011), Gemini (5012), Codex (5013) with streaming support
- Existing interceptors: circuit breaker (3 failures), retry (max 4, exp backoff), adaptive timeout (P95)
- FallbackCache in `services/fallback.py` is in-memory with TTL support - good abstraction to extend
- MCP Python SDK uses `FastMCP` with `@mcp.tool()` decorator, supports async
- 200+ existing tests using pytest-asyncio with sophisticated mocking

### Self-Review (Gap Analysis)

**Identified Gaps (addressed in plan)**:
- Proto changes may be needed for parallel workflow - **ADDRESSED**: Using workflow engine at gateway level, no proto changes
- Stream multiplexing for parallel - **ADDRESSED**: SSE includes step_id for client-side demux
- Redis connection management - **ADDRESSED**: Using connection pool in gateway lifespan

---

## Work Objectives

### Core Objective
Transform Synapse from a sequential workflow executor into a flexible multi-pattern orchestrator with real-time streaming, proper caching, and native tool integration.

### Concrete Deliverables
- `gateway/api_gateway.py`: Enhanced workflow endpoint + SSE streaming endpoints
- `gateway/workflow_engine.py`: NEW - Workflow orchestration logic
- `gateway/error_handlers.py`: NEW - Structured error responses
- `services/redis_cache.py`: NEW - Redis caching abstraction
- `services/fallback.py`: Modified to use Redis backend
- `mcp_server/`: NEW directory with MCP server implementation
- `SKILL.md`: NEW - Skill documentation with quick commands
- `docker-compose.yml`: Modified to include Redis service
- `pyproject.toml`: Modified to include new dependencies

### Definition of Done
- [ ] `pytest tests/` passes with all new tests
- [ ] `docker-compose up` starts all services including Redis
- [ ] `/api/v1/workflow` accepts `workflow_type` parameter
- [ ] SSE streaming endpoints respond with event streams
- [ ] MCP server responds to tool invocations
- [ ] Existing tests continue to pass (backward compatibility)

### Must Have
- Backward compatibility: existing `/api/v1/workflow` calls work unchanged
- TDD: tests written before implementation
- Redis in docker-compose with health check
- MCP stdio transport support
- Structured error responses with `retry_after`

### Must NOT Have (Guardrails)
- **NO** authentication/authorization changes
- **NO** proto/gRPC changes (use gateway-level orchestration)
- **NO** new gRPC services (use existing 3)
- **NO** UI/Dashboard changes
- **NO** breaking changes to existing API contracts
- **NO** external Redis (managed in docker-compose)

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: YES (pytest-asyncio, conftest.py with mocking)
- **User wants tests**: TDD
- **Framework**: pytest with pytest-asyncio

### TDD Approach

Each TODO follows RED-GREEN-REFACTOR:

**Task Structure:**
1. **RED**: Write failing test first
   - Test file: `tests/test_{feature}.py`
   - Test command: `pytest tests/test_{feature}.py -v`
   - Expected: FAIL (test exists, implementation doesn't)
2. **GREEN**: Implement minimum code to pass
   - Command: `pytest tests/test_{feature}.py -v`
   - Expected: PASS
3. **REFACTOR**: Clean up while keeping green
   - Command: `pytest tests/ -v`
   - Expected: PASS (all tests)

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
└── Task 1: Add dependencies (redis, mcp, sse-starlette)

Wave 2 (After Wave 1):
├── Task 2: Redis caching layer
├── Task 3: Workflow engine (parallel/swarm patterns)
├── Task 4: Structured error handling
└── Task 5: MCP server skeleton

Wave 3 (After Wave 2):
├── Task 6: SSE streaming endpoints
├── Task 7: Integrate Redis into FallbackCache
├── Task 8: Complete MCP tools
└── Task 9: SKILL.md creation

Wave 4 (Final):
├── Task 10: Docker-compose Redis integration
└── Task 11: Integration tests + final verification

Critical Path: Task 1 → Task 2 → Task 7 → Task 10 → Task 11
Parallel Speedup: ~50% faster than sequential
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2,3,4,5 | None (foundation) |
| 2 | 1 | 7,10 | 3,4,5 |
| 3 | 1 | 6 | 2,4,5 |
| 4 | 1 | 6 | 2,3,5 |
| 5 | 1 | 8 | 2,3,4 |
| 6 | 3,4 | 11 | 7,8,9 |
| 7 | 2 | 10 | 6,8,9 |
| 8 | 5 | 11 | 6,7,9 |
| 9 | None | 11 | 6,7,8 |
| 10 | 2,7 | 11 | 9 |
| 11 | 6,7,8,9,10 | None | None (final) |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Dispatch |
|------|-------|---------------------|
| 1 | 1 | `delegate_task(category="quick", ...)` |
| 2 | 2,3,4,5 | `delegate_task(category="unspecified-high", run_in_background=true)` x4 |
| 3 | 6,7,8,9 | `delegate_task(category="unspecified-high", run_in_background=true)` x4 |
| 4 | 10,11 | `delegate_task(category="quick", ...)` then final verification |

---

## TODOs

### Task 1: Add Project Dependencies

**What to do**:
- Add `redis>=5.0.0` to pyproject.toml dependencies
- Add `mcp>=1.0.0` to pyproject.toml dependencies  
- Add `sse-starlette>=1.6.0` to pyproject.toml dependencies
- Run `uv sync` or `pip install -e .` to install

**Must NOT do**:
- Do not modify any other files
- Do not change existing dependencies

**Recommended Agent Profile**:
- **Category**: `quick`
  - Reason: Single file edit, trivial task
- **Skills**: `[]`
  - No special skills needed for dependency addition

**Parallelization**:
- **Can Run In Parallel**: NO
- **Parallel Group**: Wave 1 (solo - foundation)
- **Blocks**: Tasks 2, 3, 4, 5
- **Blocked By**: None

**References**:

**Pattern References**:
- `pyproject.toml:10-21` - Existing dependency format and structure

**External References**:
- `redis-py` docs: https://redis-py.readthedocs.io/
- `mcp` Python SDK: https://github.com/modelcontextprotocol/python-sdk
- `sse-starlette` docs: https://github.com/sysid/sse-starlette

**Acceptance Criteria**:

**TDD**:
- [ ] No test needed - dependency installation verified by other tasks

**Manual Execution Verification**:
- [ ] Command: `cd /Users/jangyoung/Documents/Github/Synapse && uv sync`
- [ ] Expected: Successfully installs all dependencies
- [ ] Verify: `python -c "import redis; import mcp; import sse_starlette; print('OK')"`

**Commit**: YES
- Message: `feat(deps): add redis, mcp, and sse-starlette dependencies`
- Files: `pyproject.toml`
- Pre-commit: `uv sync`

---

### Task 2: Implement Redis Caching Layer

**What to do**:
- Create `services/redis_cache.py` with:
  - `RedisCacheConfig` dataclass (host, port, db, password, ttl, max_connections)
  - `RedisCache` class with async methods: `get`, `set`, `delete`, `clear`, `exists`
  - `RedisCachePool` for connection management
  - Key generation strategy compatible with existing FallbackCache
- Write tests first in `tests/test_redis_cache.py`
- Use `redis.asyncio` for async Redis operations

**Must NOT do**:
- Do not modify FallbackCache yet (that's Task 7)
- Do not add Redis to docker-compose yet (that's Task 10)
- Do not add authentication to Redis (keep simple)

**Recommended Agent Profile**:
- **Category**: `unspecified-high`
  - Reason: New module creation with async patterns and testing
- **Skills**: `[]`
  - Standard Python async patterns, no special skills needed

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 2 (with Tasks 3, 4, 5)
- **Blocks**: Tasks 7, 10
- **Blocked By**: Task 1

**References**:

**Pattern References**:
- `services/fallback.py:47-123` - FallbackCache implementation (interface to match)
- `services/fallback.py:24-35` - CacheEntry dataclass pattern
- `gateway/connection_pool.py:1-100` - Connection pooling pattern for async resources

**Test References**:
- `tests/conftest.py:1-60` - Test fixture patterns and async setup
- `tests/conftest.py:82-109` - Mock continuation patterns

**External References**:
- redis-py async: https://redis-py.readthedocs.io/en/stable/examples/asyncio_examples.html

**WHY Each Reference Matters**:
- `fallback.py:47-123`: Match the `get`/`set`/`clear` interface for drop-in replacement
- `connection_pool.py`: Follow the same connection lifecycle pattern for Redis pool
- `conftest.py`: Use same async testing patterns for consistency

**Acceptance Criteria**:

**TDD**:
- [ ] Test file created: `tests/test_redis_cache.py`
- [ ] Tests cover: get/set/delete/ttl expiration/connection failure handling
- [ ] `pytest tests/test_redis_cache.py -v` → PASS (using mocked Redis)

**Manual Execution Verification**:
- [ ] Using Python REPL (with local Redis or mock):
  ```python
  from services.redis_cache import RedisCache, RedisCacheConfig
  config = RedisCacheConfig(host="localhost", port=6379)
  cache = RedisCache(config)
  # Verify interface matches FallbackCache
  ```

**Commit**: YES
- Message: `feat(cache): add Redis caching layer with async support`
- Files: `services/redis_cache.py`, `tests/test_redis_cache.py`
- Pre-commit: `pytest tests/test_redis_cache.py -v`

---

### Task 3: Implement Workflow Engine with Parallel/Swarm Patterns

**What to do**:
- Create `gateway/workflow_engine.py` with:
  - `WorkflowType` enum: `PIPELINE`, `PARALLEL`, `SWARM`
  - `WorkflowStep` dataclass: agent, action, depends_on, config
  - `WorkflowEngine` class with:
    - `execute_pipeline()`: Sequential execution (existing behavior)
    - `execute_parallel()`: `asyncio.gather()` for independent steps
    - `execute_swarm()`: Dynamic step generation based on results
  - `WorkflowResult` with step results and timing
- Write tests first in `tests/test_workflow_engine.py`
- Use dependency tracking for parallel execution

**Must NOT do**:
- Do not modify `api_gateway.py` yet (that's Task 6)
- Do not modify proto files
- Do not implement actual AI calls (mock in tests, use pools in integration)

**Recommended Agent Profile**:
- **Category**: `unspecified-high`
  - Reason: Core business logic with async orchestration patterns
- **Skills**: `[]`
  - Standard Python async patterns

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 2 (with Tasks 2, 4, 5)
- **Blocks**: Task 6
- **Blocked By**: Task 1

**References**:

**Pattern References**:
- `gateway/api_gateway.py:303-335` - Current sequential workflow (to replace)
- `gateway/api_gateway.py:58-73` - Client creation patterns
- `clients/resilient_client.py:1-50` - Client interface for service calls

**API/Type References**:
- `gateway/api_gateway.py:28-51` - Request models (PlanRequest, etc.)

**External References**:
- asyncio.gather: https://docs.python.org/3/library/asyncio-task.html#asyncio.gather

**WHY Each Reference Matters**:
- `api_gateway.py:303-335`: This is the code being replaced - understand current flow
- `resilient_client.py`: Interface for actual service calls the engine will use

**Acceptance Criteria**:

**TDD**:
- [ ] Test file created: `tests/test_workflow_engine.py`
- [ ] Tests cover: pipeline execution, parallel execution, swarm execution, dependency resolution
- [ ] `pytest tests/test_workflow_engine.py -v` → PASS

**Manual Execution Verification**:
- [ ] Using Python REPL:
  ```python
  from gateway.workflow_engine import WorkflowEngine, WorkflowType, WorkflowStep
  engine = WorkflowEngine()
  # Verify enum values
  assert WorkflowType.PIPELINE.value == "pipeline"
  assert WorkflowType.PARALLEL.value == "parallel"
  assert WorkflowType.SWARM.value == "swarm"
  ```

**Commit**: YES
- Message: `feat(workflow): add WorkflowEngine with pipeline/parallel/swarm patterns`
- Files: `gateway/workflow_engine.py`, `tests/test_workflow_engine.py`
- Pre-commit: `pytest tests/test_workflow_engine.py -v`

---

### Task 4: Implement Structured Error Handling

**What to do**:
- Create `gateway/error_handlers.py` with:
  - `SynapseError` base exception class
  - `ServiceUnavailableError`, `ServiceTimeoutError`, `ValidationError` subclasses
  - `ErrorResponse` Pydantic model with:
    - `error_code`: str (e.g., "SERVICE_UNAVAILABLE")
    - `message`: str
    - `retry_after`: int | None (seconds)
    - `fallback_available`: bool
    - `fallback_service`: str | None
    - `request_id`: str
    - `timestamp`: datetime
  - `error_handler` FastAPI exception handler function
  - `calculate_retry_after()` function using circuit breaker state
- Write tests first in `tests/test_error_handlers.py`

**Must NOT do**:
- Do not modify `api_gateway.py` yet (integration in Task 6)
- Do not change existing error responses until integrated

**Recommended Agent Profile**:
- **Category**: `unspecified-high`
  - Reason: Error handling patterns with Pydantic models
- **Skills**: `[]`
  - Standard FastAPI patterns

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 2 (with Tasks 2, 3, 5)
- **Blocks**: Task 6
- **Blocked By**: Task 1

**References**:

**Pattern References**:
- `gateway/api_gateway.py:190-208` - Current HTTPException usage (to replace)
- `services/interceptors/circuit_breaker.py:1-100` - Circuit breaker state for retry calculation
- `services/fallback.py:163-201` - FallbackManager for fallback_available logic

**API/Type References**:
- `gateway/api_gateway.py:28-51` - Pydantic model patterns

**External References**:
- FastAPI exception handlers: https://fastapi.tiangolo.com/tutorial/handling-errors/

**WHY Each Reference Matters**:
- `api_gateway.py:190-208`: Current error pattern being enhanced
- `circuit_breaker.py`: Source of retry timing information
- `fallback.py:163-201`: Determines if fallback is available

**Acceptance Criteria**:

**TDD**:
- [ ] Test file created: `tests/test_error_handlers.py`
- [ ] Tests cover: ErrorResponse serialization, retry_after calculation, exception handler integration
- [ ] `pytest tests/test_error_handlers.py -v` → PASS

**Manual Execution Verification**:
- [ ] Using Python REPL:
  ```python
  from gateway.error_handlers import ErrorResponse, ServiceUnavailableError
  err = ErrorResponse(
      error_code="SERVICE_UNAVAILABLE",
      message="Test",
      retry_after=30,
      fallback_available=True,
      fallback_service="claude",
      request_id="test-123",
      timestamp=datetime.now()
  )
  print(err.model_dump_json())
  ```

**Commit**: YES
- Message: `feat(errors): add structured error handling with retry guidance`
- Files: `gateway/error_handlers.py`, `tests/test_error_handlers.py`
- Pre-commit: `pytest tests/test_error_handlers.py -v`

---

### Task 5: Create MCP Server Skeleton

**What to do**:
- Create `mcp_server/` directory with:
  - `__init__.py`
  - `synapse_mcp.py` with FastMCP server:
    - Initialize `FastMCP("Synapse")` 
    - Define tool stubs (not implemented yet):
      - `@mcp.tool() synapse_plan(task: str, constraints: list[str] | None)`
      - `@mcp.tool() synapse_analyze(content: str, analysis_type: str)`
      - `@mcp.tool() synapse_review(code: str, language: str)`
      - `@mcp.tool() synapse_execute(command: str, working_dir: str | None, timeout: int)`
      - `@mcp.tool() synapse_workflow(task: str, workflow_type: str, constraints: list[str] | None)`
    - Tools should return placeholder responses for now
    - Main entry point for stdio transport
- Write tests first in `tests/test_mcp_server.py`

**Must NOT do**:
- Do not implement actual HTTP calls to gateway yet (that's Task 8)
- Do not add to SKILL.md yet (that's Task 9)

**Recommended Agent Profile**:
- **Category**: `unspecified-high`
  - Reason: New integration with MCP SDK
- **Skills**: `[]`
  - MCP patterns from Context7 docs already gathered

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 2 (with Tasks 2, 3, 4)
- **Blocks**: Task 8
- **Blocked By**: Task 1

**References**:

**Pattern References**:
- `gateway/api_gateway.py:28-51` - Request models to mirror in MCP tools
- `gateway/api_gateway.py:201-235` - Endpoint signatures to expose as tools

**External References**:
- MCP FastMCP pattern (from Context7):
  ```python
  from mcp.server.fastmcp import FastMCP
  mcp = FastMCP("Demo")
  @mcp.tool()
  def add(a: int, b: int) -> int:
      """Add two numbers"""
      return a + b
  if __name__ == "__main__":
      mcp.run()  # stdio transport by default
  ```

**WHY Each Reference Matters**:
- `api_gateway.py:28-51`: MCP tool parameters should match API request models
- `api_gateway.py:201-235`: Tool signatures mirror these endpoints

**Acceptance Criteria**:

**TDD**:
- [ ] Test file created: `tests/test_mcp_server.py`
- [ ] Tests cover: tool registration, tool schema validation, placeholder responses
- [ ] `pytest tests/test_mcp_server.py -v` → PASS

**Manual Execution Verification**:
- [ ] Command: `python -c "from mcp_server.synapse_mcp import mcp; print(mcp.name)"`
- [ ] Expected: `Synapse`
- [ ] Verify tools registered: Check `mcp._tools` contains 5 tools

**Commit**: YES
- Message: `feat(mcp): add MCP server skeleton with tool stubs`
- Files: `mcp_server/__init__.py`, `mcp_server/synapse_mcp.py`, `tests/test_mcp_server.py`
- Pre-commit: `pytest tests/test_mcp_server.py -v`

---

### Task 6: Add SSE Streaming Endpoints to Gateway

**What to do**:
- Modify `gateway/api_gateway.py` to:
  - Add `WorkflowRequest` model extending `PlanRequest` with:
    - `workflow_type: str = "pipeline"` (default for backward compat)
    - `model_config: dict | None = None`
  - Add `from sse_starlette.sse import EventSourceResponse`
  - Add streaming endpoints:
    - `GET /api/v1/workflow/stream` - SSE workflow progress
    - `GET /api/v1/claude/plan/stream` - SSE plan generation progress
  - Modify `/api/v1/workflow` to use `WorkflowEngine`
  - Integrate `error_handlers.py` exception handlers
- Each SSE event should include: `event`, `data`, `id`, `step_id` (for parallel demux)
- Write tests in `tests/test_gateway_streaming.py`

**Must NOT do**:
- Do not remove existing endpoints
- Do not change response format of existing endpoints

**Recommended Agent Profile**:
- **Category**: `unspecified-high`
  - Reason: Complex integration with multiple components
- **Skills**: `[]`
  - Standard FastAPI + SSE patterns

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 3 (with Tasks 7, 8, 9)
- **Blocks**: Task 11
- **Blocked By**: Tasks 3, 4

**References**:

**Pattern References**:
- `gateway/api_gateway.py:303-335` - Current workflow endpoint (to enhance)
- `gateway/api_gateway.py:141-165` - Middleware and app creation patterns
- `gateway/workflow_engine.py` (Task 3) - WorkflowEngine to integrate

**API/Type References**:
- `gateway/api_gateway.py:28-51` - Existing request models
- `gateway/error_handlers.py` (Task 4) - Error handling to integrate

**External References**:
- sse-starlette: https://github.com/sysid/sse-starlette
- FastAPI StreamingResponse: https://fastapi.tiangolo.com/advanced/custom-response/

**WHY Each Reference Matters**:
- `api_gateway.py:303-335`: Code being modified - understand current implementation
- `workflow_engine.py`: New engine to use for workflow execution
- `error_handlers.py`: New error handling to integrate

**Acceptance Criteria**:

**TDD**:
- [ ] Test file created: `tests/test_gateway_streaming.py`
- [ ] Tests cover: SSE event format, workflow_type parameter, backward compatibility
- [ ] `pytest tests/test_gateway_streaming.py -v` → PASS

**Manual Execution Verification**:
- [ ] Start gateway: `uvicorn gateway.api_gateway:app --port 8000`
- [ ] Test SSE: `curl -N http://localhost:8000/api/v1/workflow/stream -d '{"task":"test"}' -H "Content-Type: application/json"`
- [ ] Expected: Server-Sent Events with `event:` and `data:` lines
- [ ] Test backward compat: `curl http://localhost:8000/api/v1/workflow -d '{"task":"test"}' -H "Content-Type: application/json"`
- [ ] Expected: Same JSON response as before

**Commit**: YES
- Message: `feat(gateway): add SSE streaming endpoints and workflow types`
- Files: `gateway/api_gateway.py`, `tests/test_gateway_streaming.py`
- Pre-commit: `pytest tests/test_gateway_streaming.py tests/test_gateway*.py -v`

---

### Task 7: Integrate Redis into FallbackCache

**What to do**:
- Modify `services/fallback.py` to:
  - Add `RedisFallbackCache` class that extends/wraps `FallbackCache`
  - Use `RedisCache` (from Task 2) as storage backend
  - Keep in-memory `FallbackCache` as fallback when Redis unavailable
  - Add `use_redis: bool = False` to `FallbackConfig`
  - Modify `FallbackManager` to accept cache backend configuration
  - Update `create_default_fallback_manager()` to optionally use Redis
- Write tests in `tests/test_fallback_redis.py`

**Must NOT do**:
- Do not remove existing in-memory functionality
- Do not make Redis required (optional enhancement)

**Recommended Agent Profile**:
- **Category**: `unspecified-high`
  - Reason: Integration between two caching systems
- **Skills**: `[]`
  - Standard Python patterns

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 3 (with Tasks 6, 8, 9)
- **Blocks**: Task 10
- **Blocked By**: Task 2

**References**:

**Pattern References**:
- `services/fallback.py:47-123` - FallbackCache to extend
- `services/fallback.py:163-211` - FallbackManager to modify
- `services/redis_cache.py` (Task 2) - RedisCache to use

**Test References**:
- `tests/test_redis_cache.py` (Task 2) - Redis testing patterns

**WHY Each Reference Matters**:
- `fallback.py:47-123`: Interface to maintain for compatibility
- `redis_cache.py`: Backend implementation to integrate

**Acceptance Criteria**:

**TDD**:
- [ ] Test file created: `tests/test_fallback_redis.py`
- [ ] Tests cover: Redis backend usage, fallback to in-memory, config toggling
- [ ] `pytest tests/test_fallback_redis.py -v` → PASS

**Manual Execution Verification**:
- [ ] Using Python REPL:
  ```python
  from services.fallback import FallbackConfig, FallbackManager
  config = FallbackConfig(use_redis=True)
  manager = FallbackManager(config)
  # Verify Redis backend is used when configured
  ```

**Commit**: YES
- Message: `feat(fallback): integrate Redis backend with fallback to in-memory`
- Files: `services/fallback.py`, `tests/test_fallback_redis.py`
- Pre-commit: `pytest tests/test_fallback*.py -v`

---

### Task 8: Complete MCP Tools with Gateway Integration

**What to do**:
- Modify `mcp_server/synapse_mcp.py` to:
  - Add `httpx.AsyncClient` for HTTP calls to gateway
  - Add `GATEWAY_URL` config (default: `http://localhost:8000`)
  - Implement all 5 tools with actual HTTP calls:
    - `synapse_plan`: POST `/api/v1/claude/plan`
    - `synapse_analyze`: POST `/api/v1/gemini/analyze`
    - `synapse_review`: POST `/api/v1/gemini/review`
    - `synapse_execute`: POST `/api/v1/codex/execute`
    - `synapse_workflow`: POST `/api/v1/workflow` with workflow_type
  - Add error handling for gateway failures
  - Add `__main__` block for direct execution
- Update tests in `tests/test_mcp_server.py`

**Must NOT do**:
- Do not add authentication headers (keep simple)
- Do not implement SSE streaming in MCP (use polling for now)

**Recommended Agent Profile**:
- **Category**: `unspecified-high`
  - Reason: HTTP integration with error handling
- **Skills**: `[]`
  - Standard httpx patterns

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 3 (with Tasks 6, 7, 9)
- **Blocks**: Task 11
- **Blocked By**: Task 5

**References**:

**Pattern References**:
- `mcp_server/synapse_mcp.py` (Task 5) - Skeleton to complete
- `gateway/api_gateway.py:201-300` - Endpoint paths and request formats

**API/Type References**:
- `gateway/api_gateway.py:28-51` - Request models for httpx payloads

**External References**:
- httpx async: https://www.python-httpx.org/async/

**WHY Each Reference Matters**:
- `synapse_mcp.py` (Task 5): Build on existing skeleton
- `api_gateway.py:201-300`: Exact endpoint paths to call

**Acceptance Criteria**:

**TDD**:
- [ ] Test file updated: `tests/test_mcp_server.py`
- [ ] Tests cover: HTTP calls (mocked), error handling, response formatting
- [ ] `pytest tests/test_mcp_server.py -v` → PASS

**Manual Execution Verification**:
- [ ] Start gateway: `docker-compose up gateway`
- [ ] Run MCP tool test:
  ```python
  import asyncio
  from mcp_server.synapse_mcp import synapse_plan
  result = asyncio.run(synapse_plan("Test task", None))
  print(result)
  ```
- [ ] Expected: Plan result from gateway

**Commit**: YES
- Message: `feat(mcp): complete MCP tools with gateway HTTP integration`
- Files: `mcp_server/synapse_mcp.py`, `tests/test_mcp_server.py`
- Pre-commit: `pytest tests/test_mcp_server.py -v`

---

### Task 9: Create SKILL.md with Quick Commands

**What to do**:
- Create `SKILL.md` with:
  - Skill metadata (name, description, triggers)
  - Quick command examples:
    - `synapse plan "task"` - Create a plan
    - `synapse review "code"` - Review code
    - `synapse workflow "task" --type parallel` - Run workflow
  - Service health check instructions
  - Auto-detection of Docker status
  - Troubleshooting section
  - MCP server configuration for Claude Desktop/OpenCode
- Write in user-friendly format with code blocks

**Must NOT do**:
- Do not include implementation details
- Do not include internal architecture

**Recommended Agent Profile**:
- **Category**: `writing`
  - Reason: Documentation creation
- **Skills**: `[]`
  - Standard markdown patterns

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 3 (with Tasks 6, 7, 8)
- **Blocks**: Task 11
- **Blocked By**: None (can start anytime, but logically after Tasks 5, 8)

**References**:

**Pattern References**:
- `README.md` - Existing documentation style
- `mcp_server/synapse_mcp.py` (Task 8) - Tool names and signatures

**External References**:
- MCP config format for claude_desktop_config.json

**WHY Each Reference Matters**:
- `README.md`: Match existing documentation style
- `synapse_mcp.py`: Document the actual tool interfaces

**Acceptance Criteria**:

**Manual Execution Verification**:
- [ ] File created: `SKILL.md`
- [ ] Contains: Quick command examples with copy-paste ready code
- [ ] Contains: Service health check commands
- [ ] Contains: MCP configuration example
- [ ] Markdown renders correctly

**Commit**: YES
- Message: `docs(skill): add SKILL.md with quick commands and MCP config`
- Files: `SKILL.md`
- Pre-commit: N/A (documentation)

---

### Task 10: Add Redis to docker-compose.yml

**What to do**:
- Modify `docker-compose.yml` to add:
  - `redis` service using `redis:7-alpine` image
  - Port mapping: `6379:6379`
  - Health check: `redis-cli ping`
  - Volume for persistence: `redis-data`
  - Network: `synaps-network`
- Modify `gateway` service to:
  - Add `REDIS_HOST=redis` environment variable
  - Add `REDIS_PORT=6379` environment variable
  - Add `depends_on: redis`
- Add `redis-data` to volumes section

**Must NOT do**:
- Do not add Redis authentication (keep simple)
- Do not modify other services

**Recommended Agent Profile**:
- **Category**: `quick`
  - Reason: Simple docker-compose modification
- **Skills**: `[]`
  - Standard Docker patterns

**Parallelization**:
- **Can Run In Parallel**: NO
- **Parallel Group**: Wave 4 (with Task 11)
- **Blocks**: Task 11
- **Blocked By**: Tasks 2, 7

**References**:

**Pattern References**:
- `docker-compose.yml:1-130` - Existing service patterns
- `docker-compose.yml:23-62` - Service configuration pattern

**External References**:
- Redis Docker: https://hub.docker.com/_/redis

**WHY Each Reference Matters**:
- `docker-compose.yml`: Follow existing patterns for consistency

**Acceptance Criteria**:

**Manual Execution Verification**:
- [ ] Command: `docker-compose config` (validate syntax)
- [ ] Command: `docker-compose up redis -d`
- [ ] Verify: `docker exec synaps-redis redis-cli ping` → `PONG`
- [ ] Command: `docker-compose up gateway -d`
- [ ] Verify: Gateway can connect to Redis

**Commit**: YES
- Message: `infra(docker): add Redis service to docker-compose`
- Files: `docker-compose.yml`
- Pre-commit: `docker-compose config`

---

### Task 11: Integration Tests and Final Verification

**What to do**:
- Create `tests/test_integration_v2.py` with:
  - Full workflow test with all 3 types (pipeline, parallel, swarm)
  - SSE streaming verification
  - Error handling verification
  - Redis caching verification (with docker-compose)
- Run full test suite
- Verify all docker-compose services start correctly
- Test MCP server with gateway integration

**Must NOT do**:
- Do not modify implementation code
- Do not skip any verification step

**Recommended Agent Profile**:
- **Category**: `unspecified-high`
  - Reason: Comprehensive integration testing
- **Skills**: `["playwright"]`
  - For potential browser-based SSE testing

**Parallelization**:
- **Can Run In Parallel**: NO
- **Parallel Group**: Wave 4 (final)
- **Blocks**: None (final task)
- **Blocked By**: Tasks 6, 7, 8, 9, 10

**References**:

**Pattern References**:
- `tests/conftest.py` - Test fixtures
- All new test files from Tasks 2-8

**Acceptance Criteria**:

**TDD**:
- [ ] Test file created: `tests/test_integration_v2.py`
- [ ] `pytest tests/ -v` → ALL PASS

**Manual Execution Verification**:
- [ ] Command: `docker-compose up -d`
- [ ] Verify all services healthy: `docker-compose ps`
- [ ] Test workflow types:
  ```bash
  curl -X POST http://localhost:8000/api/v1/workflow \
    -H "Content-Type: application/json" \
    -d '{"task": "test", "workflow_type": "parallel"}'
  ```
- [ ] Test SSE streaming:
  ```bash
  curl -N http://localhost:8000/api/v1/workflow/stream \
    -H "Content-Type: application/json" \
    -d '{"task": "test"}'
  ```
- [ ] Test MCP server (if gateway running):
  ```bash
  python -m mcp_server.synapse_mcp
  # In another terminal, test via MCP client
  ```

**Commit**: YES
- Message: `test(integration): add comprehensive integration tests for v2 features`
- Files: `tests/test_integration_v2.py`
- Pre-commit: `pytest tests/ -v`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `feat(deps): add redis, mcp, and sse-starlette dependencies` | pyproject.toml | uv sync |
| 2 | `feat(cache): add Redis caching layer with async support` | services/redis_cache.py, tests/test_redis_cache.py | pytest |
| 3 | `feat(workflow): add WorkflowEngine with pipeline/parallel/swarm patterns` | gateway/workflow_engine.py, tests/test_workflow_engine.py | pytest |
| 4 | `feat(errors): add structured error handling with retry guidance` | gateway/error_handlers.py, tests/test_error_handlers.py | pytest |
| 5 | `feat(mcp): add MCP server skeleton with tool stubs` | mcp_server/*, tests/test_mcp_server.py | pytest |
| 6 | `feat(gateway): add SSE streaming endpoints and workflow types` | gateway/api_gateway.py, tests/test_gateway_streaming.py | pytest |
| 7 | `feat(fallback): integrate Redis backend with fallback to in-memory` | services/fallback.py, tests/test_fallback_redis.py | pytest |
| 8 | `feat(mcp): complete MCP tools with gateway HTTP integration` | mcp_server/synapse_mcp.py, tests/test_mcp_server.py | pytest |
| 9 | `docs(skill): add SKILL.md with quick commands and MCP config` | SKILL.md | N/A |
| 10 | `infra(docker): add Redis service to docker-compose` | docker-compose.yml | docker-compose config |
| 11 | `test(integration): add comprehensive integration tests for v2 features` | tests/test_integration_v2.py | pytest |

---

## Success Criteria

### Verification Commands
```bash
# Run full test suite
pytest tests/ -v --tb=short

# Start all services
docker-compose up -d

# Verify services
docker-compose ps  # All services "Up" and healthy

# Test workflow types
curl -X POST http://localhost:8000/api/v1/workflow \
  -H "Content-Type: application/json" \
  -d '{"task": "test parallel", "workflow_type": "parallel"}'
# Expected: {"steps": [...], "workflow_completed": true}

# Test SSE streaming
curl -N http://localhost:8000/api/v1/workflow/stream \
  -H "Content-Type: application/json" \
  -d '{"task": "test streaming"}'
# Expected: event: step\ndata: {...}\n\n (multiple events)

# Test error handling
curl http://localhost:8000/api/v1/claude/plan \
  -H "Content-Type: application/json" \
  -d '{}' 
# Expected: {"error_code": "VALIDATION_ERROR", "retry_after": null, ...}

# Test Redis caching
docker exec synaps-redis redis-cli keys "*"
# Expected: Cached keys after workflow execution
```

### Final Checklist
- [ ] All "Must Have" features present
- [ ] All "Must NOT Have" guardrails respected
- [ ] All 200+ existing tests still pass
- [ ] New tests for all new features
- [ ] Docker-compose starts all services including Redis
- [ ] Backward compatibility maintained for existing clients
