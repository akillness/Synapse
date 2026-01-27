import logging
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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


@app.post("/api/v1/workflow")
async def run_workflow(request: PlanRequest):
    if not pools:
        raise HTTPException(503, "Service not ready")

    results = {"steps": []}

    claude_pool = pools.get_pool("claude")
    gemini_pool = pools.get_pool("gemini")
    codex_pool = pools.get_pool("codex")

    async with claude_pool.acquire() as claude:
        plan = await claude.create_plan(request.task, request.constraints)
        results["steps"].append({"agent": "claude", "action": "plan", "result": plan})

    async with gemini_pool.acquire() as gemini:
        analysis = await gemini.analyze(request.task, "requirements")
        results["steps"].append({"agent": "gemini", "action": "analyze", "result": analysis})

    async with claude_pool.acquire() as claude:
        code = await claude.generate_code(request.task)
        results["steps"].append({"agent": "claude", "action": "generate_code", "result": code})

    async with gemini_pool.acquire() as gemini:
        review = await gemini.review_code(code["code"])
        results["steps"].append({"agent": "gemini", "action": "review", "result": review})

    async with codex_pool.acquire() as codex:
        exec_result = await codex.execute("echo 'Workflow completed!'")
        results["steps"].append({"agent": "codex", "action": "execute", "result": exec_result})

    results["workflow_completed"] = True
    return results


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
