import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from gateway.load_balancer import (
    LeastConnectionsStrategy,
    LeastResponseTimeStrategy,
    LoadBalancer,
    MultiServiceLoadBalancer,
    RoundRobinStrategy,
    ServiceEndpoint,
    WeightedStrategy,
)


class TestServiceEndpoint:
    def test_address_property(self):
        endpoint = ServiceEndpoint(host="127.0.0.1", port=5000)

        assert endpoint.address == "127.0.0.1:5000"

    def test_record_success_updates_metrics(self):
        endpoint = ServiceEndpoint(host="127.0.0.1", port=5000)

        endpoint.record_success(1.0)
        endpoint.record_success(2.0)

        assert endpoint.success_count == 2
        assert endpoint.failure_count == 0
        assert endpoint.avg_response_time == 1.5

    def test_record_failure_increments_count(self):
        endpoint = ServiceEndpoint(host="127.0.0.1", port=5000)

        endpoint.record_failure()
        endpoint.record_failure()

        assert endpoint.failure_count == 2

    def test_marks_unhealthy_after_failures(self):
        endpoint = ServiceEndpoint(host="127.0.0.1", port=5000)

        endpoint.record_failure()
        endpoint.record_failure()
        assert endpoint.healthy is True

        endpoint.record_failure()
        assert endpoint.healthy is False

    def test_success_resets_failure_count(self):
        endpoint = ServiceEndpoint(host="127.0.0.1", port=5000)

        endpoint.record_failure()
        endpoint.record_failure()
        endpoint.record_success(1.0)

        assert endpoint.failure_count == 0

    def test_response_time_history_limit(self):
        endpoint = ServiceEndpoint(host="127.0.0.1", port=5000)

        for i in range(150):
            endpoint.record_success(float(i))

        assert len(endpoint._response_times) == 100


class TestRoundRobinStrategy:
    def test_selects_endpoints_in_order(self, service_endpoints):
        strategy = RoundRobinStrategy()

        selected1 = strategy.select(service_endpoints)
        selected2 = strategy.select(service_endpoints)
        selected3 = strategy.select(service_endpoints)
        selected4 = strategy.select(service_endpoints)

        assert selected1.port == 5001
        assert selected2.port == 5002
        assert selected3.port == 5003
        assert selected4.port == 5001

    def test_skips_unhealthy_endpoints(self, service_endpoints):
        strategy = RoundRobinStrategy()
        service_endpoints[0].healthy = False

        selected1 = strategy.select(service_endpoints)
        selected2 = strategy.select(service_endpoints)
        strategy.select(service_endpoints)

        assert selected1.port in [5002, 5003]
        assert selected2.port in [5002, 5003]

    def test_returns_none_when_all_unhealthy(self, service_endpoints):
        strategy = RoundRobinStrategy()
        for endpoint in service_endpoints:
            endpoint.healthy = False

        selected = strategy.select(service_endpoints)

        assert selected is None


class TestWeightedStrategy:
    def test_selects_based_on_weight(self):
        endpoints = [
            ServiceEndpoint(host="127.0.0.1", port=5001, weight=10),
            ServiceEndpoint(host="127.0.0.1", port=5002, weight=1),
        ]
        strategy = WeightedStrategy()

        selections = [strategy.select(endpoints).port for _ in range(100)]
        count_5001 = selections.count(5001)
        count_5002 = selections.count(5002)

        assert count_5001 > count_5002

    def test_skips_unhealthy_endpoints(self):
        endpoints = [
            ServiceEndpoint(host="127.0.0.1", port=5001, weight=10, healthy=False),
            ServiceEndpoint(host="127.0.0.1", port=5002, weight=1),
        ]
        strategy = WeightedStrategy()

        for _ in range(10):
            selected = strategy.select(endpoints)
            assert selected.port == 5002


class TestLeastConnectionsStrategy:
    def test_selects_endpoint_with_least_connections(self, service_endpoints):
        strategy = LeastConnectionsStrategy()
        strategy._connections = {
            "127.0.0.1:5001": 5,
            "127.0.0.1:5002": 2,
            "127.0.0.1:5003": 8,
        }

        selected = strategy.select(service_endpoints)

        assert selected.port == 5002

    def test_increment_and_decrement(self):
        strategy = LeastConnectionsStrategy()

        strategy.increment("127.0.0.1:5000")
        strategy.increment("127.0.0.1:5000")
        assert strategy._connections["127.0.0.1:5000"] == 2

        strategy.decrement("127.0.0.1:5000")
        assert strategy._connections["127.0.0.1:5000"] == 1

    def test_decrement_does_not_go_negative(self):
        strategy = LeastConnectionsStrategy()

        strategy.decrement("127.0.0.1:5000")

        assert strategy._connections.get("127.0.0.1:5000", 0) == 0


class TestLeastResponseTimeStrategy:
    def test_selects_endpoint_with_lowest_response_time(self, service_endpoints):
        strategy = LeastResponseTimeStrategy()
        service_endpoints[0].avg_response_time = 100.0
        service_endpoints[1].avg_response_time = 50.0
        service_endpoints[2].avg_response_time = 200.0

        selected = strategy.select(service_endpoints)

        assert selected.port == 5002

    def test_handles_zero_response_time(self, service_endpoints):
        strategy = LeastResponseTimeStrategy()
        service_endpoints[0].avg_response_time = 0.0
        service_endpoints[1].avg_response_time = 50.0

        selected = strategy.select(service_endpoints)

        assert selected.port == 5002


class TestLoadBalancer:
    @pytest.mark.asyncio
    async def test_add_endpoint(self):
        lb = LoadBalancer("test")

        lb.add_endpoint("127.0.0.1", 5000)

        assert len(lb._endpoints) == 1
        assert lb._endpoints[0].address == "127.0.0.1:5000"

    @pytest.mark.asyncio
    async def test_remove_endpoint(self):
        lb = LoadBalancer("test")
        lb.add_endpoint("127.0.0.1", 5000)
        lb.add_endpoint("127.0.0.1", 5001)

        lb.remove_endpoint("127.0.0.1", 5000)

        assert len(lb._endpoints) == 1
        assert lb._endpoints[0].port == 5001

    @pytest.mark.asyncio
    async def test_get_endpoint_uses_strategy(self):
        lb = LoadBalancer("test", RoundRobinStrategy())
        lb.add_endpoint("127.0.0.1", 5000)
        lb.add_endpoint("127.0.0.1", 5001)

        ep1 = lb.get_endpoint()
        ep2 = lb.get_endpoint()

        assert ep1.port == 5000
        assert ep2.port == 5001

    @pytest.mark.asyncio
    async def test_record_success_updates_endpoint(self):
        lb = LoadBalancer("test")
        lb.add_endpoint("127.0.0.1", 5000)
        endpoint = lb.get_endpoint()

        lb.record_success(endpoint, 1.5)

        assert endpoint.success_count == 1
        assert endpoint.avg_response_time == 1.5

    @pytest.mark.asyncio
    async def test_record_failure_updates_endpoint(self):
        lb = LoadBalancer("test")
        lb.add_endpoint("127.0.0.1", 5000)
        endpoint = lb.get_endpoint()

        lb.record_failure(endpoint)

        assert endpoint.failure_count == 1

    @pytest.mark.asyncio
    async def test_get_stats(self):
        lb = LoadBalancer("test")
        lb.add_endpoint("127.0.0.1", 5000)
        lb.add_endpoint("127.0.0.1", 5001)
        lb._endpoints[1].healthy = False

        stats = lb.get_stats()

        assert stats["service"] == "test"
        assert stats["total_endpoints"] == 2
        assert stats["healthy_endpoints"] == 1
        assert len(stats["endpoints"]) == 2

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        lb = LoadBalancer("test", health_check_interval=0.1)

        async def health_checker(host, port):
            return True

        lb.set_health_checker(health_checker)

        await lb.start()
        assert lb._health_check_task is not None

        await lb.stop()


class TestLoadBalancerHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_updates_endpoint_status(self):
        lb = LoadBalancer("test", health_check_interval=0.1)
        lb.add_endpoint("127.0.0.1", 5000)

        check_count = 0

        async def health_checker(host, port):
            nonlocal check_count
            check_count += 1
            return check_count <= 1

        lb.set_health_checker(health_checker)

        await lb.start()
        await asyncio.sleep(0.25)
        await lb.stop()

        assert check_count >= 2


class TestMultiServiceLoadBalancer:
    @pytest.mark.asyncio
    async def test_add_and_get_service(self):
        multi_lb = MultiServiceLoadBalancer()
        lb = LoadBalancer("test")

        multi_lb.add_service("test", lb)

        retrieved = multi_lb.get_balancer("test")

        assert retrieved is lb

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self):
        multi_lb = MultiServiceLoadBalancer()

        retrieved = multi_lb.get_balancer("nonexistent")

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_start_all(self):
        multi_lb = MultiServiceLoadBalancer()

        lb1 = LoadBalancer("service1")
        lb2 = LoadBalancer("service2")

        multi_lb.add_service("service1", lb1)
        multi_lb.add_service("service2", lb2)

        await multi_lb.start_all()
        await multi_lb.stop_all()

    @pytest.mark.asyncio
    async def test_get_all_stats(self):
        multi_lb = MultiServiceLoadBalancer()

        lb1 = LoadBalancer("service1")
        lb1.add_endpoint("127.0.0.1", 5000)

        lb2 = LoadBalancer("service2")
        lb2.add_endpoint("127.0.0.1", 5001)

        multi_lb.add_service("service1", lb1)
        multi_lb.add_service("service2", lb2)

        stats = multi_lb.get_all_stats()

        assert "service1" in stats
        assert "service2" in stats
        assert stats["service1"]["total_endpoints"] == 1
        assert stats["service2"]["total_endpoints"] == 1
