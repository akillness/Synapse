import asyncio
import logging
import time
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from typing import Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class PoolConfig:
    min_size: int = 2
    max_size: int = 10
    max_idle_time: float = 300.0
    acquire_timeout: float = 30.0
    health_check_interval: float = 60.0


@dataclass
class PooledConnection(Generic[T]):
    connection: T
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    use_count: int = 0
    is_healthy: bool = True

    @property
    def idle_time(self) -> float:
        return time.time() - self.last_used_at

    def mark_used(self):
        self.last_used_at = time.time()
        self.use_count += 1


class ConnectionPool(Generic[T]):
    def __init__(
        self,
        name: str,
        factory,
        config: PoolConfig | None = None,
        health_checker=None,
    ):
        self.name = name
        self.factory = factory
        self.config = config or PoolConfig()
        self.health_checker = health_checker

        self._pool: asyncio.Queue[PooledConnection[T]] = asyncio.Queue(
            maxsize=self.config.max_size
        )
        self._all_connections: list[PooledConnection[T]] = []
        self._lock = asyncio.Lock()
        self._closed = False
        self._health_check_task: asyncio.Task | None = None

        self._total_acquired = 0
        self._total_released = 0
        self._total_created = 0
        self._total_destroyed = 0

    async def initialize(self):
        async with self._lock:
            for _ in range(self.config.min_size):
                await self._create_connection()

        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info(
            f"Pool '{self.name}' initialized with {self.config.min_size} connections"
        )

    async def _create_connection(self) -> PooledConnection[T]:
        conn = await self.factory()
        pooled = PooledConnection(connection=conn)
        self._all_connections.append(pooled)
        await self._pool.put(pooled)
        self._total_created += 1
        return pooled

    async def _destroy_connection(self, pooled: PooledConnection[T]):
        if pooled in self._all_connections:
            self._all_connections.remove(pooled)
        self._total_destroyed += 1

        if hasattr(pooled.connection, "disconnect"):
            try:
                await pooled.connection.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting: {e}")

    @asynccontextmanager
    async def acquire(self):
        if self._closed:
            raise RuntimeError(f"Pool '{self.name}' is closed")

        pooled: PooledConnection[T] | None = None

        try:
            pooled = await asyncio.wait_for(
                self._pool.get(), timeout=self.config.acquire_timeout
            )

            if not pooled.is_healthy:
                await self._destroy_connection(pooled)
                async with self._lock:
                    pooled = await self._create_connection()
                    await self._pool.get()

            pooled.mark_used()
            self._total_acquired += 1

            yield pooled.connection

        except TimeoutError:
            async with self._lock:
                if len(self._all_connections) < self.config.max_size:
                    pooled = await self._create_connection()
                    await self._pool.get()
                    pooled.mark_used()
                    self._total_acquired += 1
                    yield pooled.connection
                else:
                    raise RuntimeError(f"Pool '{self.name}' exhausted")
        finally:
            if pooled and not self._closed:
                self._total_released += 1
                await self._pool.put(pooled)

    async def _health_check_loop(self):
        while not self._closed:
            await asyncio.sleep(self.config.health_check_interval)

            if self.health_checker:
                for pooled in self._all_connections[:]:
                    try:
                        pooled.is_healthy = await self.health_checker(pooled.connection)
                    except Exception:
                        pooled.is_healthy = False

            async with self._lock:
                for pooled in self._all_connections[:]:
                    if pooled.idle_time > self.config.max_idle_time:
                        if len(self._all_connections) > self.config.min_size:
                            await self._destroy_connection(pooled)

    async def close(self):
        self._closed = True

        if self._health_check_task:
            self._health_check_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._health_check_task

        for pooled in self._all_connections[:]:
            await self._destroy_connection(pooled)

        logger.info(f"Pool '{self.name}' closed")

    def get_stats(self) -> dict:
        return {
            "name": self.name,
            "current_size": len(self._all_connections),
            "available": self._pool.qsize(),
            "total_acquired": self._total_acquired,
            "total_released": self._total_released,
            "total_created": self._total_created,
            "total_destroyed": self._total_destroyed,
        }


class MultiServicePool:
    def __init__(self):
        self._pools: dict[str, ConnectionPool] = {}

    def add_pool(self, name: str, pool: ConnectionPool):
        self._pools[name] = pool

    def get_pool(self, name: str) -> ConnectionPool | None:
        return self._pools.get(name)

    async def initialize_all(self):
        for pool in self._pools.values():
            await pool.initialize()

    async def close_all(self):
        for pool in self._pools.values():
            await pool.close()

    def get_all_stats(self) -> dict[str, dict]:
        return {name: pool.get_stats() for name, pool in self._pools.items()}
