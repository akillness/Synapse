import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from gateway.connection_pool import (
    ConnectionPool,
    MultiServicePool,
    PoolConfig,
    PooledConnection,
)


class TestPoolConfig:
    def test_default_values(self):
        config = PoolConfig()

        assert config.min_size == 2
        assert config.max_size == 10
        assert config.max_idle_time == 300.0
        assert config.acquire_timeout == 30.0
        assert config.health_check_interval == 60.0


class TestPooledConnection:
    def test_idle_time_calculation(self):
        conn = PooledConnection(connection=MagicMock())
        initial_idle = conn.idle_time

        assert initial_idle >= 0

    def test_mark_used_updates_timestamp(self):
        conn = PooledConnection(connection=MagicMock())
        initial_use_count = conn.use_count

        conn.mark_used()

        assert conn.use_count == initial_use_count + 1


class TestConnectionPool:
    @pytest.mark.asyncio
    async def test_initialize_creates_min_connections(
        self, pool_config, mock_connection_factory, mock_health_checker
    ):
        pool = ConnectionPool(
            "test",
            mock_connection_factory,
            pool_config,
            mock_health_checker,
        )

        await pool.initialize()

        try:
            assert len(pool._all_connections) == pool_config.min_size
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_acquire_returns_connection(
        self, pool_config, mock_connection_factory, mock_health_checker
    ):
        pool = ConnectionPool(
            "test",
            mock_connection_factory,
            pool_config,
            mock_health_checker,
        )

        await pool.initialize()

        try:
            async with pool.acquire() as conn:
                assert conn is not None
                assert hasattr(conn, "id")
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_acquire_marks_connection_used(
        self, pool_config, mock_connection_factory, mock_health_checker
    ):
        pool = ConnectionPool(
            "test",
            mock_connection_factory,
            pool_config,
            mock_health_checker,
        )

        await pool.initialize()

        try:
            async with pool.acquire():
                pass

            assert pool._total_acquired == 1
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_release_returns_connection_to_pool(
        self, pool_config, mock_connection_factory, mock_health_checker
    ):
        pool = ConnectionPool(
            "test",
            mock_connection_factory,
            pool_config,
            mock_health_checker,
        )

        await pool.initialize()

        try:
            async with pool.acquire():
                pass

            assert pool._total_released == 1
            assert pool._pool.qsize() == pool_config.min_size
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_creates_new_connection_when_exhausted(self, mock_connection_factory):
        config = PoolConfig(min_size=1, max_size=3, acquire_timeout=0.1)
        pool = ConnectionPool("test", mock_connection_factory, config)

        await pool.initialize()

        try:
            conns = []
            async with pool.acquire() as c1:
                conns.append(c1)
                async with pool.acquire() as c2:
                    conns.append(c2)
                    assert len(pool._all_connections) == 2
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_raises_when_max_size_reached(self, mock_connection_factory):
        config = PoolConfig(min_size=1, max_size=1, acquire_timeout=0.1)
        pool = ConnectionPool("test", mock_connection_factory, config)

        await pool.initialize()

        try:
            async with pool.acquire():
                with pytest.raises(RuntimeError, match="exhausted"):
                    async with pool.acquire():
                        pass
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_close_destroys_all_connections(
        self, pool_config, mock_connection_factory, mock_health_checker
    ):
        pool = ConnectionPool(
            "test",
            mock_connection_factory,
            pool_config,
            mock_health_checker,
        )

        await pool.initialize()
        await pool.close()

        assert pool._closed is True
        assert len(pool._all_connections) == 0

    @pytest.mark.asyncio
    async def test_acquire_on_closed_pool_raises(
        self, pool_config, mock_connection_factory, mock_health_checker
    ):
        pool = ConnectionPool(
            "test",
            mock_connection_factory,
            pool_config,
            mock_health_checker,
        )

        await pool.initialize()
        await pool.close()

        with pytest.raises(RuntimeError, match="closed"):
            async with pool.acquire():
                pass

    @pytest.mark.asyncio
    async def test_get_stats(self, pool_config, mock_connection_factory, mock_health_checker):
        pool = ConnectionPool(
            "test",
            mock_connection_factory,
            pool_config,
            mock_health_checker,
        )

        await pool.initialize()

        try:
            async with pool.acquire():
                stats = pool.get_stats()

                assert stats["name"] == "test"
                assert stats["current_size"] == pool_config.min_size
                assert stats["total_acquired"] == 1
        finally:
            await pool.close()


class TestConnectionPoolHealthCheck:
    @pytest.mark.asyncio
    async def test_unhealthy_connection_is_replaced(self, mock_connection_factory):
        health_results = [True, True, False]
        call_count = 0

        async def health_checker(conn):
            nonlocal call_count
            result = health_results[call_count % len(health_results)]
            call_count += 1
            return result

        config = PoolConfig(min_size=1, max_size=3, health_check_interval=0.1)
        pool = ConnectionPool("test", mock_connection_factory, config, health_checker)

        await pool.initialize()

        try:
            pooled = pool._all_connections[0]
            pooled.is_healthy = False

            async with pool.acquire():
                pass

            assert pool._total_created >= 2
        finally:
            await pool.close()


class TestMultiServicePool:
    @pytest.mark.asyncio
    async def test_add_and_get_pool(
        self, pool_config, mock_connection_factory, mock_health_checker
    ):
        multi_pool = MultiServicePool()
        pool = ConnectionPool(
            "test",
            mock_connection_factory,
            pool_config,
            mock_health_checker,
        )

        multi_pool.add_pool("test", pool)

        retrieved = multi_pool.get_pool("test")

        assert retrieved is pool

    @pytest.mark.asyncio
    async def test_get_nonexistent_pool_returns_none(self):
        multi_pool = MultiServicePool()

        retrieved = multi_pool.get_pool("nonexistent")

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_initialize_all(self, pool_config, mock_connection_factory, mock_health_checker):
        multi_pool = MultiServicePool()

        pool1 = ConnectionPool("pool1", mock_connection_factory, pool_config, mock_health_checker)
        pool2 = ConnectionPool("pool2", mock_connection_factory, pool_config, mock_health_checker)

        multi_pool.add_pool("pool1", pool1)
        multi_pool.add_pool("pool2", pool2)

        await multi_pool.initialize_all()

        try:
            assert len(pool1._all_connections) == pool_config.min_size
            assert len(pool2._all_connections) == pool_config.min_size
        finally:
            await multi_pool.close_all()

    @pytest.mark.asyncio
    async def test_close_all(self, pool_config, mock_connection_factory, mock_health_checker):
        multi_pool = MultiServicePool()

        pool1 = ConnectionPool("pool1", mock_connection_factory, pool_config, mock_health_checker)
        pool2 = ConnectionPool("pool2", mock_connection_factory, pool_config, mock_health_checker)

        multi_pool.add_pool("pool1", pool1)
        multi_pool.add_pool("pool2", pool2)

        await multi_pool.initialize_all()
        await multi_pool.close_all()

        assert pool1._closed is True
        assert pool2._closed is True

    @pytest.mark.asyncio
    async def test_get_all_stats(self, pool_config, mock_connection_factory, mock_health_checker):
        multi_pool = MultiServicePool()

        pool1 = ConnectionPool("pool1", mock_connection_factory, pool_config, mock_health_checker)
        pool2 = ConnectionPool("pool2", mock_connection_factory, pool_config, mock_health_checker)

        multi_pool.add_pool("pool1", pool1)
        multi_pool.add_pool("pool2", pool2)

        await multi_pool.initialize_all()

        try:
            stats = multi_pool.get_all_stats()

            assert "pool1" in stats
            assert "pool2" in stats
            assert stats["pool1"]["name"] == "pool1"
            assert stats["pool2"]["name"] == "pool2"
        finally:
            await multi_pool.close_all()
