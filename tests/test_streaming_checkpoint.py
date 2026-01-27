import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.streaming_checkpoint import (
    ResumableStreamWrapper,
    StreamCheckpoint,
    StreamCheckpointManager,
    StreamState,
    create_resumable_stream,
)


class TestStreamState:
    def test_last_checkpoint_returns_none_when_empty(self):
        state = StreamState(stream_id="test", started_at=1000.0)

        assert state.last_checkpoint is None

    def test_last_checkpoint_returns_latest(self):
        state = StreamState(stream_id="test", started_at=1000.0)
        cp1 = StreamCheckpoint(
            stream_id="test",
            last_sequence=1,
            last_content="first",
            progress_percent=10.0,
            timestamp=1001.0,
        )
        cp2 = StreamCheckpoint(
            stream_id="test",
            last_sequence=2,
            last_content="second",
            progress_percent=20.0,
            timestamp=1002.0,
        )
        state.checkpoints = [cp1, cp2]

        assert state.last_checkpoint == cp2

    def test_can_resume_when_incomplete_with_checkpoint(self):
        state = StreamState(stream_id="test", started_at=1000.0)
        state.checkpoints.append(
            StreamCheckpoint(
                stream_id="test",
                last_sequence=1,
                last_content="test",
                progress_percent=50.0,
                timestamp=1001.0,
            )
        )

        assert state.can_resume is True

    def test_cannot_resume_when_completed(self):
        state = StreamState(stream_id="test", started_at=1000.0, completed=True)
        state.checkpoints.append(
            StreamCheckpoint(
                stream_id="test",
                last_sequence=1,
                last_content="test",
                progress_percent=100.0,
                timestamp=1001.0,
            )
        )

        assert state.can_resume is False

    def test_cannot_resume_without_checkpoint(self):
        state = StreamState(stream_id="test", started_at=1000.0)

        assert state.can_resume is False


class TestStreamCheckpointManager:
    @pytest.mark.asyncio
    async def test_start_stream_creates_state(self, checkpoint_manager):
        state = await checkpoint_manager.start_stream("stream-1")

        assert state.stream_id == "stream-1"
        assert state.completed is False

    @pytest.mark.asyncio
    async def test_checkpoint_at_interval(self, checkpoint_manager):
        await checkpoint_manager.start_stream("stream-1")

        cp1 = await checkpoint_manager.checkpoint("stream-1", 0, "msg0", 10.0)
        cp2 = await checkpoint_manager.checkpoint("stream-1", 1, "msg1", 20.0)
        cp3 = await checkpoint_manager.checkpoint("stream-1", 2, "msg2", 30.0)

        assert cp1 is not None
        assert cp2 is None
        assert cp3 is not None

    @pytest.mark.asyncio
    async def test_checkpoint_at_100_percent(self, checkpoint_manager):
        await checkpoint_manager.start_stream("stream-1")

        cp = await checkpoint_manager.checkpoint("stream-1", 1, "final", 100.0)

        assert cp is not None

    @pytest.mark.asyncio
    async def test_get_resume_point(self, checkpoint_manager):
        await checkpoint_manager.start_stream("stream-1")
        await checkpoint_manager.checkpoint("stream-1", 0, "msg0", 10.0)
        await checkpoint_manager.checkpoint("stream-1", 2, "msg2", 30.0)

        resume = await checkpoint_manager.get_resume_point("stream-1")

        assert resume.last_sequence == 2

    @pytest.mark.asyncio
    async def test_no_resume_point_for_completed_stream(self, checkpoint_manager):
        await checkpoint_manager.start_stream("stream-1")
        await checkpoint_manager.checkpoint("stream-1", 0, "msg0", 50.0)
        await checkpoint_manager.complete_stream("stream-1")

        resume = await checkpoint_manager.get_resume_point("stream-1")

        assert resume is None

    @pytest.mark.asyncio
    async def test_complete_stream(self, checkpoint_manager):
        await checkpoint_manager.start_stream("stream-1")
        await checkpoint_manager.complete_stream("stream-1")

        state = await checkpoint_manager.get_state("stream-1")

        assert state.completed is True

    @pytest.mark.asyncio
    async def test_fail_stream(self, checkpoint_manager):
        await checkpoint_manager.start_stream("stream-1")
        await checkpoint_manager.fail_stream("stream-1", "Connection lost")

        state = await checkpoint_manager.get_state("stream-1")

        assert state.error == "Connection lost"

    @pytest.mark.asyncio
    async def test_tracks_total_messages(self, checkpoint_manager):
        await checkpoint_manager.start_stream("stream-1")
        await checkpoint_manager.checkpoint("stream-1", 0, "msg", 10.0)
        await checkpoint_manager.checkpoint("stream-1", 1, "msg", 20.0)
        await checkpoint_manager.checkpoint("stream-1", 9, "msg", 90.0)

        state = await checkpoint_manager.get_state("stream-1")

        assert state.total_messages == 10

    @pytest.mark.asyncio
    async def test_get_stats(self, checkpoint_manager):
        await checkpoint_manager.start_stream("stream-1")
        await checkpoint_manager.start_stream("stream-2")
        await checkpoint_manager.complete_stream("stream-1")
        await checkpoint_manager.fail_stream("stream-2", "error")

        stats = checkpoint_manager.get_stats()

        assert stats["total_streams"] == 2
        assert stats["completed_streams"] == 1
        assert stats["failed_streams"] == 1


class TestStreamCheckpointManagerLimits:
    @pytest.mark.asyncio
    async def test_evicts_oldest_when_max_reached(self):
        manager = StreamCheckpointManager(max_streams=2)

        await manager.start_stream("stream-1")
        await asyncio.sleep(0.01)
        await manager.start_stream("stream-2")
        await asyncio.sleep(0.01)
        await manager.start_stream("stream-3")

        state1 = await manager.get_state("stream-1")
        state3 = await manager.get_state("stream-3")

        assert state1 is None
        assert state3 is not None

    @pytest.mark.asyncio
    async def test_cleans_expired_streams(self):
        manager = StreamCheckpointManager(ttl=0.05)

        await manager.start_stream("old-stream")
        await asyncio.sleep(0.1)
        await manager.start_stream("new-stream")

        old_state = await manager.get_state("old-stream")
        new_state = await manager.get_state("new-stream")

        assert old_state is None
        assert new_state is not None


class TestStreamCheckpointMetadata:
    @pytest.mark.asyncio
    async def test_checkpoint_with_metadata(self, checkpoint_manager):
        await checkpoint_manager.start_stream("stream-1")

        cp = await checkpoint_manager.checkpoint(
            "stream-1", 0, "msg", 10.0, metadata={"key": "value"}
        )

        assert cp.metadata == {"key": "value"}


@dataclass
class MockStreamMessage:
    content: str
    progress_percent: float


class TestResumableStreamWrapper:
    @pytest.mark.asyncio
    async def test_wraps_stream_and_yields_messages(self, checkpoint_manager):
        messages = [
            MockStreamMessage("msg1", 25.0),
            MockStreamMessage("msg2", 50.0),
            MockStreamMessage("msg3", 75.0),
            MockStreamMessage("msg4", 100.0),
        ]

        async def stream_factory():
            for msg in messages:
                yield msg

        wrapper = ResumableStreamWrapper(
            "stream-1",
            checkpoint_manager,
            stream_factory,
        )

        received = []
        async for msg in wrapper:
            received.append(msg)

        assert len(received) == 4
        assert received[0].content == "msg1"

    @pytest.mark.asyncio
    async def test_completes_stream_on_success(self, checkpoint_manager):
        messages = [MockStreamMessage("msg1", 100.0)]

        async def stream_factory():
            for msg in messages:
                yield msg

        wrapper = ResumableStreamWrapper(
            "stream-1",
            checkpoint_manager,
            stream_factory,
        )

        async for _ in wrapper:
            pass

        state = await checkpoint_manager.get_state("stream-1")
        assert state.completed is True

    @pytest.mark.asyncio
    async def test_fails_stream_on_error(self, checkpoint_manager):
        async def failing_stream():
            yield MockStreamMessage("msg1", 25.0)
            raise ValueError("Stream error")

        wrapper = ResumableStreamWrapper(
            "stream-1",
            checkpoint_manager,
            failing_stream,
        )

        with pytest.raises(ValueError):
            async for _ in wrapper:
                pass

        state = await checkpoint_manager.get_state("stream-1")
        assert state.error is not None

    @pytest.mark.asyncio
    async def test_resumes_from_checkpoint(self, checkpoint_manager):
        await checkpoint_manager.start_stream("stream-1")
        await checkpoint_manager.checkpoint("stream-1", 2, "resumed", 50.0)

        full_messages = [
            MockStreamMessage("msg3", 60.0),
            MockStreamMessage("msg4", 80.0),
            MockStreamMessage("msg5", 100.0),
        ]

        async def stream_factory():
            for msg in full_messages:
                yield msg

        def resume_factory(from_sequence):
            assert from_sequence == 2
            return stream_factory()

        wrapper = ResumableStreamWrapper(
            "stream-1",
            checkpoint_manager,
            stream_factory,
            resume_factory,
        )

        received = []
        async for msg in wrapper:
            received.append(msg)

        assert len(received) == 3


class TestCreateResumableStream:
    @pytest.mark.asyncio
    async def test_creates_wrapper(self):
        async def stream_factory():
            yield "msg"

        wrapper = await create_resumable_stream("stream-1", stream_factory)

        assert isinstance(wrapper, ResumableStreamWrapper)
        assert wrapper.stream_id == "stream-1"
