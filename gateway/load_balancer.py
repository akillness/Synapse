import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class ServiceEndpoint:
    host: str
    port: int
    weight: int = 1
    healthy: bool = True
    last_check: float = field(default_factory=time.time)
    failure_count: int = 0
    success_count: int = 0
    avg_response_time: float = 0.0
    _response_times: List[float] = field(default_factory=list)

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    def record_success(self, response_time: float):
        self.success_count += 1
        self.failure_count = 0
        self._response_times.append(response_time)
        if len(self._response_times) > 100:
            self._response_times.pop(0)
        self.avg_response_time = sum(self._response_times) / len(self._response_times)

    def record_failure(self):
        self.failure_count += 1
        if self.failure_count >= 3:
            self.healthy = False


class LoadBalancerStrategy(ABC):
    @abstractmethod
    def select(self, endpoints: List[ServiceEndpoint]) -> Optional[ServiceEndpoint]:
        pass


class RoundRobinStrategy(LoadBalancerStrategy):
    def __init__(self):
        self._index = 0
        self._lock = asyncio.Lock()

    def select(self, endpoints: List[ServiceEndpoint]) -> Optional[ServiceEndpoint]:
        healthy = [e for e in endpoints if e.healthy]
        if not healthy:
            return None

        selected = healthy[self._index % len(healthy)]
        self._index = (self._index + 1) % len(healthy)
        return selected


class WeightedStrategy(LoadBalancerStrategy):
    def select(self, endpoints: List[ServiceEndpoint]) -> Optional[ServiceEndpoint]:
        healthy = [e for e in endpoints if e.healthy]
        if not healthy:
            return None

        total_weight = sum(e.weight for e in healthy)
        r = random.uniform(0, total_weight)
        cumulative = 0

        for endpoint in healthy:
            cumulative += endpoint.weight
            if r <= cumulative:
                return endpoint

        return healthy[-1]


class LeastConnectionsStrategy(LoadBalancerStrategy):
    def __init__(self):
        self._connections: Dict[str, int] = {}

    def select(self, endpoints: List[ServiceEndpoint]) -> Optional[ServiceEndpoint]:
        healthy = [e for e in endpoints if e.healthy]
        if not healthy:
            return None

        min_conns = float("inf")
        selected = None

        for endpoint in healthy:
            conns = self._connections.get(endpoint.address, 0)
            if conns < min_conns:
                min_conns = conns
                selected = endpoint

        return selected

    def increment(self, address: str):
        self._connections[address] = self._connections.get(address, 0) + 1

    def decrement(self, address: str):
        if address in self._connections:
            self._connections[address] = max(0, self._connections[address] - 1)


class LeastResponseTimeStrategy(LoadBalancerStrategy):
    def select(self, endpoints: List[ServiceEndpoint]) -> Optional[ServiceEndpoint]:
        healthy = [e for e in endpoints if e.healthy]
        if not healthy:
            return None

        return min(
            healthy,
            key=lambda e: e.avg_response_time
            if e.avg_response_time > 0
            else float("inf"),
        )


class LoadBalancer:
    def __init__(
        self,
        service_name: str,
        strategy: Optional[LoadBalancerStrategy] = None,
        health_check_interval: float = 30.0,
    ):
        self.service_name = service_name
        self.strategy = strategy or RoundRobinStrategy()
        self.health_check_interval = health_check_interval

        self._endpoints: List[ServiceEndpoint] = []
        self._health_checker = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    def add_endpoint(self, host: str, port: int, weight: int = 1):
        endpoint = ServiceEndpoint(host=host, port=port, weight=weight)
        self._endpoints.append(endpoint)
        logger.info(f"Added endpoint {endpoint.address} to {self.service_name}")

    def remove_endpoint(self, host: str, port: int):
        self._endpoints = [
            e for e in self._endpoints if not (e.host == host and e.port == port)
        ]

    def set_health_checker(self, checker):
        self._health_checker = checker

    async def start(self):
        if self._health_checker:
            self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def stop(self):
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

    async def _health_check_loop(self):
        while True:
            await asyncio.sleep(self.health_check_interval)

            for endpoint in self._endpoints:
                try:
                    healthy = await self._health_checker(endpoint.host, endpoint.port)
                    endpoint.healthy = healthy
                    endpoint.last_check = time.time()
                    if healthy:
                        endpoint.failure_count = 0
                except Exception:
                    endpoint.healthy = False
                    endpoint.failure_count += 1

    def get_endpoint(self) -> Optional[ServiceEndpoint]:
        return self.strategy.select(self._endpoints)

    def record_success(self, endpoint: ServiceEndpoint, response_time: float):
        endpoint.record_success(response_time)

    def record_failure(self, endpoint: ServiceEndpoint):
        endpoint.record_failure()

    def get_stats(self) -> Dict:
        return {
            "service": self.service_name,
            "total_endpoints": len(self._endpoints),
            "healthy_endpoints": sum(1 for e in self._endpoints if e.healthy),
            "endpoints": [
                {
                    "address": e.address,
                    "healthy": e.healthy,
                    "weight": e.weight,
                    "success_count": e.success_count,
                    "failure_count": e.failure_count,
                    "avg_response_time_ms": round(e.avg_response_time * 1000, 2),
                }
                for e in self._endpoints
            ],
        }


class MultiServiceLoadBalancer:
    def __init__(self):
        self._balancers: Dict[str, LoadBalancer] = {}

    def add_service(self, name: str, balancer: LoadBalancer):
        self._balancers[name] = balancer

    def get_balancer(self, name: str) -> Optional[LoadBalancer]:
        return self._balancers.get(name)

    async def start_all(self):
        for balancer in self._balancers.values():
            await balancer.start()

    async def stop_all(self):
        for balancer in self._balancers.values():
            await balancer.stop()

    def get_all_stats(self) -> Dict[str, Dict]:
        return {name: b.get_stats() for name, b in self._balancers.items()}
