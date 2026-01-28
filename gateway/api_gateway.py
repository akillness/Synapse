import asyncio
import json
import logging
import sys
import time
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent))

from clients.resilient_client import (
    ResilientClaudeClient,
    ResilientCodexClient,
    ResilientGeminiClient,
)
from gateway.connection_pool import ConnectionPool, MultiServicePool, PoolConfig
from gateway.load_balancer import (
    LoadBalancer,
    MultiServiceLoadBalancer,
    RoundRobinStrategy,
)

logger = logging.getLogger(__name__)


class WorkflowType(str, Enum):
    """Workflow execution type"""

    PIPELINE = "pipeline"  # Sequential: plan → analyze → code → review → execute
    PARALLEL = "parallel"  # Parallel execution of independent tasks
    SWARM = "swarm"  # Self-organizing workers


class ModelConfig(BaseModel):
    """Model configuration for each agent role"""

    planner: str = "claude-sonnet-4.5"
    analyst: str = "gemini-3-pro-preview"
    coder: str = "claude-sonnet-4.5"
    reviewer: str = "gemini-3-pro-preview"
    executor: str = "gpt-5.2"


class PlanRequest(BaseModel):
    task: str
    constraints: list[str] | None = None


class CodeRequest(BaseModel):
    description: str
    language: str = "python"


class AnalyzeRequest(BaseModel):
    content: str
    analysis_type: str = "general"


class ReviewRequest(BaseModel):
    code: str
    language: str = "python"


class ExecuteRequest(BaseModel):
    command: str
    working_dir: str | None = None
    timeout: int = 30


class WorkflowRequest(BaseModel):
    """Enhanced workflow request with workflow type and model configuration"""

    task: str
    constraints: list[str] | None = None
    workflow_type: WorkflowType = WorkflowType.PIPELINE
    model_config_: ModelConfig | None = Field(default=None, alias="model_config")
    stream: bool = False


class EnhancedErrorResponse(BaseModel):
    """Enhanced error response with retry and fallback information"""

    error: str
    detail: str
    retry_after: int | None = None
    fallback_available: bool = False
    fallback_service: str | None = None
    request_id: str | None = None


pools: MultiServicePool | None = None
load_balancers: MultiServiceLoadBalancer | None = None


async def create_claude_client():
    client = ResilientClaudeClient()
    await client.connect()
    return client


async def create_gemini_client():
    client = ResilientGeminiClient()
    await client.connect()
    return client


async def create_codex_client():
    client = ResilientCodexClient()
    await client.connect()
    return client


async def health_check_client(client) -> bool:
    try:
        result = await client.health_check()
        return result.get("status") == "SERVING"
    except Exception:
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pools, load_balancers

    pools = MultiServicePool()

    claude_pool = ConnectionPool(
        "claude",
        create_claude_client,
        PoolConfig(min_size=2, max_size=5),
        health_check_client,
    )
    gemini_pool = ConnectionPool(
        "gemini",
        create_gemini_client,
        PoolConfig(min_size=2, max_size=5),
        health_check_client,
    )
    codex_pool = ConnectionPool(
        "codex",
        create_codex_client,
        PoolConfig(min_size=2, max_size=5),
        health_check_client,
    )

    pools.add_pool("claude", claude_pool)
    pools.add_pool("gemini", gemini_pool)
    pools.add_pool("codex", codex_pool)

    await pools.initialize_all()

    load_balancers = MultiServiceLoadBalancer()

    claude_lb = LoadBalancer("claude", RoundRobinStrategy())
    claude_lb.add_endpoint("127.0.0.1", 5011)

    gemini_lb = LoadBalancer("gemini", RoundRobinStrategy())
    gemini_lb.add_endpoint("127.0.0.1", 5012)

    codex_lb = LoadBalancer("codex", RoundRobinStrategy())
    codex_lb.add_endpoint("127.0.0.1", 5013)

    load_balancers.add_service("claude", claude_lb)
    load_balancers.add_service("gemini", gemini_lb)
    load_balancers.add_service("codex", codex_lb)

    await load_balancers.start_all()

    logger.info("API Gateway started")

    yield

    await pools.close_all()
    await load_balancers.stop_all()
    logger.info("API Gateway stopped")


def create_app() -> FastAPI:
    application = FastAPI(
        title="Synaps AI Agent Gateway",
        description="Multi-Process AI Agent System API Gateway",
        version="1.0.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.middleware("http")
    async def add_timing_header(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        response.headers["X-Response-Time"] = f"{duration * 1000:.2f}ms"
        return response

    return application


app = create_app()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "gateway"}


@app.get("/metrics")
async def metrics():
    result = {"pools": {}, "load_balancers": {}}

    if pools:
        result["pools"] = pools.get_all_stats()
    if load_balancers:
        result["load_balancers"] = load_balancers.get_all_stats()

    return result


@app.get("/api/v1/claude/health")
async def claude_health():
    if not pools:
        raise HTTPException(503, "Service not ready")

    pool = pools.get_pool("claude")
    if not pool:
        raise HTTPException(503, "Claude pool not available")

    async with pool.acquire() as client:
        return await client.health_check()


@app.post("/api/v1/claude/plan")
async def create_plan(request: PlanRequest):
    if not pools:
        raise HTTPException(503, "Service not ready")

    pool = pools.get_pool("claude")
    if not pool:
        raise HTTPException(503, "Claude pool not available")

    start = time.perf_counter()
    async with pool.acquire() as client:
        result = await client.create_plan(request.task, request.constraints)
        duration = time.perf_counter() - start

        if load_balancers:
            lb = load_balancers.get_balancer("claude")
            if lb:
                endpoint = lb.get_endpoint()
                if endpoint:
                    lb.record_success(endpoint, duration)

        return result


@app.post("/api/v1/claude/code")
async def generate_code(request: CodeRequest):
    if not pools:
        raise HTTPException(503, "Service not ready")

    pool = pools.get_pool("claude")
    if not pool:
        raise HTTPException(503, "Claude pool not available")

    async with pool.acquire() as client:
        return await client.generate_code(request.description, request.language)


@app.get("/api/v1/gemini/health")
async def gemini_health():
    if not pools:
        raise HTTPException(503, "Service not ready")

    pool = pools.get_pool("gemini")
    if not pool:
        raise HTTPException(503, "Gemini pool not available")

    async with pool.acquire() as client:
        return await client.health_check()


@app.post("/api/v1/gemini/analyze")
async def analyze(request: AnalyzeRequest):
    if not pools:
        raise HTTPException(503, "Service not ready")

    pool = pools.get_pool("gemini")
    if not pool:
        raise HTTPException(503, "Gemini pool not available")

    async with pool.acquire() as client:
        return await client.analyze(request.content, request.analysis_type)


@app.post("/api/v1/gemini/review")
async def review_code(request: ReviewRequest):
    if not pools:
        raise HTTPException(503, "Service not ready")

    pool = pools.get_pool("gemini")
    if not pool:
        raise HTTPException(503, "Gemini pool not available")

    async with pool.acquire() as client:
        return await client.review_code(request.code, request.language)


@app.get("/api/v1/codex/health")
async def codex_health():
    if not pools:
        raise HTTPException(503, "Service not ready")

    pool = pools.get_pool("codex")
    if not pool:
        raise HTTPException(503, "Codex pool not available")

    async with pool.acquire() as client:
        return await client.health_check()


@app.post("/api/v1/codex/execute")
async def execute(request: ExecuteRequest):
    if not pools:
        raise HTTPException(503, "Service not ready")

    pool = pools.get_pool("codex")
    if not pool:
        raise HTTPException(503, "Codex pool not available")

    async with pool.acquire() as client:
        return await client.execute(request.command, request.working_dir, request.timeout)


def create_enhanced_error(
    error: str,
    detail: str,
    retry_after: int | None = None,
    fallback_service: str | None = None,
) -> EnhancedErrorResponse:
    return EnhancedErrorResponse(
        error=error,
        detail=detail,
        retry_after=retry_after,
        fallback_available=fallback_service is not None,
        fallback_service=fallback_service,
        request_id=f"req_{int(time.time() * 1000)}",
    )


async def execute_pipeline_workflow(
    task: str,
    constraints: list[str] | None,
    claude_pool: Any,
    gemini_pool: Any,
    codex_pool: Any,
) -> dict[str, Any]:
    """Execute workflow in sequential pipeline mode"""
    results: dict[str, Any] = {"steps": [], "workflow_type": "pipeline"}

    async with claude_pool.acquire() as claude:
        plan = await claude.create_plan(task, constraints)
        results["steps"].append({"agent": "claude", "action": "plan", "result": plan})

    async with gemini_pool.acquire() as gemini:
        analysis = await gemini.analyze(task, "requirements")
        results["steps"].append({"agent": "gemini", "action": "analyze", "result": analysis})

    async with claude_pool.acquire() as claude:
        code = await claude.generate_code(task)
        results["steps"].append({"agent": "claude", "action": "generate_code", "result": code})

    async with gemini_pool.acquire() as gemini:
        review = await gemini.review_code(code["code"])
        results["steps"].append({"agent": "gemini", "action": "review", "result": review})

    async with codex_pool.acquire() as codex:
        exec_result = await codex.execute("echo 'Workflow completed!'")
        results["steps"].append({"agent": "codex", "action": "execute", "result": exec_result})

    results["workflow_completed"] = True
    return results


async def execute_parallel_workflow(
    task: str,
    constraints: list[str] | None,
    claude_pool: Any,
    gemini_pool: Any,
    codex_pool: Any,
) -> dict[str, Any]:
    """Execute independent tasks in parallel"""
    results: dict[str, Any] = {"steps": [], "workflow_type": "parallel"}

    async def run_plan():
        async with claude_pool.acquire() as claude:
            return {
                "agent": "claude",
                "action": "plan",
                "result": await claude.create_plan(task, constraints),
            }

    async def run_analyze():
        async with gemini_pool.acquire() as gemini:
            return {
                "agent": "gemini",
                "action": "analyze",
                "result": await gemini.analyze(task, "requirements"),
            }

    async def run_code():
        async with claude_pool.acquire() as claude:
            return {
                "agent": "claude",
                "action": "generate_code",
                "result": await claude.generate_code(task),
            }

    parallel_results = await asyncio.gather(run_plan(), run_analyze(), run_code())
    results["steps"].extend(parallel_results)

    code_result = next((r for r in parallel_results if r["action"] == "generate_code"), None)
    if code_result and "code" in code_result.get("result", {}):
        async with gemini_pool.acquire() as gemini:
            review = await gemini.review_code(code_result["result"]["code"])
            results["steps"].append({"agent": "gemini", "action": "review", "result": review})

    async with codex_pool.acquire() as codex:
        exec_result = await codex.execute("echo 'Workflow completed!'")
        results["steps"].append({"agent": "codex", "action": "execute", "result": exec_result})

    results["workflow_completed"] = True
    return results


async def execute_swarm_workflow(
    task: str,
    constraints: list[str] | None,
    claude_pool: Any,
    gemini_pool: Any,
    codex_pool: Any,
) -> dict[str, Any]:
    """Execute workflow using swarm pattern - workers claim tasks from pool"""
    results: dict[str, Any] = {"steps": [], "workflow_type": "swarm"}
    task_queue: list[dict[str, Any]] = [
        {"id": 1, "type": "plan", "agent": "claude", "status": "pending"},
        {"id": 2, "type": "analyze", "agent": "gemini", "status": "pending"},
        {"id": 3, "type": "code", "agent": "claude", "status": "pending"},
    ]

    async def worker(worker_id: int, pool: Any, agent_name: str, task_types: list[str]):
        completed = []
        for t in task_queue:
            if t["agent"] == agent_name and t["type"] in task_types and t["status"] == "pending":
                t["status"] = "in_progress"
                async with pool.acquire() as client:
                    if t["type"] == "plan":
                        result = await client.create_plan(task, constraints)
                    elif t["type"] == "analyze":
                        result = await client.analyze(task, "requirements")
                    elif t["type"] == "code":
                        result = await client.generate_code(task)
                    else:
                        result = {}
                    t["status"] = "completed"
                    completed.append(
                        {
                            "agent": agent_name,
                            "action": t["type"],
                            "result": result,
                            "worker": worker_id,
                        }
                    )
        return completed

    worker_results = await asyncio.gather(
        worker(1, claude_pool, "claude", ["plan", "code"]),
        worker(2, gemini_pool, "gemini", ["analyze"]),
    )

    for worker_result in worker_results:
        results["steps"].extend(worker_result)

    results["workflow_completed"] = True
    results["tasks_processed"] = len([t for t in task_queue if t["status"] == "completed"])
    return results


@app.post("/api/v1/workflow")
async def run_workflow(request: WorkflowRequest):
    if not pools:
        error = create_enhanced_error(
            error="ServiceUnavailable",
            detail="Service pools not initialized",
            retry_after=5,
            fallback_service=None,
        )
        raise HTTPException(status_code=503, detail=error.model_dump())

    claude_pool = pools.get_pool("claude")
    gemini_pool = pools.get_pool("gemini")
    codex_pool = pools.get_pool("codex")

    if not claude_pool or not gemini_pool or not codex_pool:
        error = create_enhanced_error(
            error="PoolUnavailable",
            detail="One or more service pools not available",
            retry_after=5,
        )
        raise HTTPException(status_code=503, detail=error.model_dump())

    try:
        if request.workflow_type == WorkflowType.PIPELINE:
            return await execute_pipeline_workflow(
                request.task, request.constraints, claude_pool, gemini_pool, codex_pool
            )
        elif request.workflow_type == WorkflowType.PARALLEL:
            return await execute_parallel_workflow(
                request.task, request.constraints, claude_pool, gemini_pool, codex_pool
            )
        elif request.workflow_type == WorkflowType.SWARM:
            return await execute_swarm_workflow(
                request.task, request.constraints, claude_pool, gemini_pool, codex_pool
            )
        else:
            return await execute_pipeline_workflow(
                request.task, request.constraints, claude_pool, gemini_pool, codex_pool
            )
    except Exception as e:
        logger.exception("Workflow execution failed")
        error = create_enhanced_error(
            error="WorkflowExecutionFailed",
            detail=str(e),
            retry_after=10,
            fallback_service="gemini-2.5-flash",
        )
        raise HTTPException(status_code=500, detail=error.model_dump()) from e


async def workflow_stream_generator(request: WorkflowRequest):
    """SSE stream generator for workflow progress"""
    yield f"data: {json.dumps({'event': 'start', 'workflow_type': request.workflow_type.value})}\n\n"

    if not pools:
        yield f"data: {json.dumps({'event': 'error', 'error': 'Service not ready'})}\n\n"
        return

    claude_pool = pools.get_pool("claude")
    gemini_pool = pools.get_pool("gemini")
    codex_pool = pools.get_pool("codex")

    if not claude_pool or not gemini_pool or not codex_pool:
        yield f"data: {json.dumps({'event': 'error', 'error': 'Pools not available'})}\n\n"
        return

    steps = [
        ("plan", "claude", claude_pool, lambda c: c.create_plan(request.task, request.constraints)),
        ("analyze", "gemini", gemini_pool, lambda c: c.analyze(request.task, "requirements")),
        ("generate_code", "claude", claude_pool, lambda c: c.generate_code(request.task)),
    ]

    code_result = None
    for step_name, agent, pool, func in steps:
        yield f"data: {json.dumps({'event': 'step_start', 'step': step_name, 'agent': agent})}\n\n"
        try:
            async with pool.acquire() as client:
                result = await func(client)
                if step_name == "generate_code":
                    code_result = result
                yield f"data: {json.dumps({'event': 'step_complete', 'step': step_name, 'agent': agent, 'result': result})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'step_error', 'step': step_name, 'error': str(e)})}\n\n"

    if code_result and "code" in code_result:
        yield f"data: {json.dumps({'event': 'step_start', 'step': 'review', 'agent': 'gemini'})}\n\n"
        try:
            async with gemini_pool.acquire() as gemini:
                review = await gemini.review_code(code_result["code"])
                yield f"data: {json.dumps({'event': 'step_complete', 'step': 'review', 'agent': 'gemini', 'result': review})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'step_error', 'step': 'review', 'error': str(e)})}\n\n"

    yield f"data: {json.dumps({'event': 'step_start', 'step': 'execute', 'agent': 'codex'})}\n\n"
    try:
        async with codex_pool.acquire() as codex:
            exec_result = await codex.execute("echo 'Workflow completed!'")
            yield f"data: {json.dumps({'event': 'step_complete', 'step': 'execute', 'agent': 'codex', 'result': exec_result})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'event': 'step_error', 'step': 'execute', 'error': str(e)})}\n\n"

    yield f"data: {json.dumps({'event': 'complete', 'workflow_type': request.workflow_type.value})}\n\n"


@app.post("/api/v1/workflow/stream")
async def run_workflow_stream(request: WorkflowRequest):
    """Stream workflow execution progress via Server-Sent Events"""
    return StreamingResponse(
        workflow_stream_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/v1/workflow/legacy")
async def run_workflow_legacy(request: PlanRequest):
    """Legacy workflow endpoint for backward compatibility"""
    workflow_request = WorkflowRequest(
        task=request.task,
        constraints=request.constraints,
        workflow_type=WorkflowType.PIPELINE,
    )
    return await run_workflow(workflow_request)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
