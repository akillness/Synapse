"""
Streaming Checkpoint/Resume for gRPC
Phase 3: Resilience

스트리밍 중 장애 발생 시 체크포인트부터 재개:
- 스트림 진행 상태 저장
- 중단 지점부터 재시작
- 중복 메시지 방지
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class StreamCheckpoint:
    """스트림 체크포인트"""

    stream_id: str
    last_sequence: int
    last_content: str
    progress_percent: float
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamState:
    """스트림 상태"""

    stream_id: str
    started_at: float
    checkpoints: list[StreamCheckpoint] = field(default_factory=list)
    completed: bool = False
    error: str | None = None
    total_messages: int = 0

    @property
    def last_checkpoint(self) -> StreamCheckpoint | None:
        return self.checkpoints[-1] if self.checkpoints else None

    @property
    def can_resume(self) -> bool:
        return not self.completed and self.last_checkpoint is not None


class StreamCheckpointManager:
    """스트림 체크포인트 관리자"""

    def __init__(
        self,
        checkpoint_interval: int = 10,
        max_streams: int = 100,
        ttl: float = 3600.0,
    ):
        self.checkpoint_interval = checkpoint_interval
        self.max_streams = max_streams
        self.ttl = ttl

        self._streams: dict[str, StreamState] = {}
        self._lock = asyncio.Lock()

    async def start_stream(self, stream_id: str) -> StreamState:
        """스트림 시작"""
        async with self._lock:
            await self._cleanup_expired()

            if len(self._streams) >= self.max_streams:
                await self._evict_oldest()

            state = StreamState(
                stream_id=stream_id,
                started_at=time.time(),
            )
            self._streams[stream_id] = state

            logger.debug(f"Stream started: {stream_id}")
            return state

    async def checkpoint(
        self,
        stream_id: str,
        sequence: int,
        content: str,
        progress_percent: float,
        metadata: dict[str, Any] | None = None,
    ) -> StreamCheckpoint | None:
        """체크포인트 저장"""
        async with self._lock:
            state = self._streams.get(stream_id)
            if not state:
                return None

            state.total_messages = sequence + 1

            if sequence % self.checkpoint_interval == 0 or progress_percent >= 100:
                checkpoint = StreamCheckpoint(
                    stream_id=stream_id,
                    last_sequence=sequence,
                    last_content=content,
                    progress_percent=progress_percent,
                    timestamp=time.time(),
                    metadata=metadata or {},
                )
                state.checkpoints.append(checkpoint)

                logger.debug(
                    f"Checkpoint saved: {stream_id} seq={sequence} "
                    f"progress={progress_percent:.1f}%"
                )
                return checkpoint

            return None

    async def get_resume_point(self, stream_id: str) -> StreamCheckpoint | None:
        """재개 지점 조회"""
        async with self._lock:
            state = self._streams.get(stream_id)
            if state and state.can_resume:
                return state.last_checkpoint
            return None

    async def complete_stream(self, stream_id: str):
        """스트림 완료"""
        async with self._lock:
            state = self._streams.get(stream_id)
            if state:
                state.completed = True
                logger.debug(f"Stream completed: {stream_id}")

    async def fail_stream(self, stream_id: str, error: str):
        """스트림 실패"""
        async with self._lock:
            state = self._streams.get(stream_id)
            if state:
                state.error = error
                logger.warning(f"Stream failed: {stream_id} - {error}")

    async def get_state(self, stream_id: str) -> StreamState | None:
        """스트림 상태 조회"""
        async with self._lock:
            return self._streams.get(stream_id)

    async def _cleanup_expired(self):
        """만료된 스트림 정리"""
        now = time.time()
        expired = [
            sid
            for sid, state in self._streams.items()
            if now - state.started_at > self.ttl
        ]
        for sid in expired:
            del self._streams[sid]

    async def _evict_oldest(self):
        """가장 오래된 스트림 제거"""
        if not self._streams:
            return

        oldest = min(self._streams.keys(), key=lambda k: self._streams[k].started_at)
        del self._streams[oldest]

    def get_stats(self) -> dict[str, Any]:
        """통계"""
        active = sum(1 for s in self._streams.values() if not s.completed)
        completed = sum(1 for s in self._streams.values() if s.completed)
        failed = sum(1 for s in self._streams.values() if s.error)

        return {
            "total_streams": len(self._streams),
            "active_streams": active,
            "completed_streams": completed,
            "failed_streams": failed,
        }


class ResumableStreamWrapper:
    """재개 가능한 스트림 래퍼"""

    def __init__(
        self,
        stream_id: str,
        checkpoint_manager: StreamCheckpointManager,
        stream_factory: Callable[[], AsyncIterator[Any]],
        resume_factory: Callable[[int], AsyncIterator[Any]] | None = None,
    ):
        self.stream_id = stream_id
        self.checkpoint_manager = checkpoint_manager
        self.stream_factory = stream_factory
        self.resume_factory = resume_factory

        self._sequence = 0
        self._state: StreamState | None = None

    async def __aiter__(self) -> AsyncIterator[Any]:
        """이터레이터"""
        self._state = await self.checkpoint_manager.start_stream(self.stream_id)

        resume_point = await self.checkpoint_manager.get_resume_point(self.stream_id)

        if resume_point and self.resume_factory:
            logger.info(
                f"Resuming stream {self.stream_id} from sequence "
                f"{resume_point.last_sequence}"
            )
            self._sequence = resume_point.last_sequence
            stream = self.resume_factory(resume_point.last_sequence)
        else:
            stream = self.stream_factory()

        try:
            async for message in stream:
                self._sequence += 1

                content = getattr(message, "content", str(message))
                progress = getattr(message, "progress_percent", 0)

                await self.checkpoint_manager.checkpoint(
                    self.stream_id,
                    self._sequence,
                    content,
                    progress,
                )

                yield message

            await self.checkpoint_manager.complete_stream(self.stream_id)

        except Exception as e:
            await self.checkpoint_manager.fail_stream(self.stream_id, str(e))
            raise


async def create_resumable_stream(
    stream_id: str,
    stream_factory: Callable[[], AsyncIterator[Any]],
    checkpoint_manager: StreamCheckpointManager | None = None,
    resume_factory: Callable[[int], AsyncIterator[Any]] | None = None,
) -> ResumableStreamWrapper:
    """재개 가능한 스트림 생성 헬퍼"""
    manager = checkpoint_manager or StreamCheckpointManager()

    return ResumableStreamWrapper(
        stream_id=stream_id,
        checkpoint_manager=manager,
        stream_factory=stream_factory,
        resume_factory=resume_factory,
    )
