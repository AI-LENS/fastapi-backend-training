"""In-memory pub/sub for SSE progress events (Module 15)."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from typing import AsyncIterator
from uuid import UUID


@dataclass
class ProgressEvent:
    event_type: str  # "started" | "stage_complete" | "pipeline_complete"
    screening_id: str
    stage: str | None = None
    passed: bool | None = None
    reason: str | None = None
    eligible: bool | None = None
    failed_criteria: list[str] | None = None


class ProgressManager:
    def __init__(self) -> None:
        self._queues: dict[UUID, list[asyncio.Queue]] = defaultdict(list)

    async def emit(self, screening_id: UUID, event: ProgressEvent) -> None:
        for q in self._queues.get(screening_id, []):
            await q.put(event)

    async def subscribe(self, screening_id: UUID) -> AsyncIterator[ProgressEvent]:
        q: asyncio.Queue = asyncio.Queue()
        self._queues[screening_id].append(q)
        try:
            while True:
                event = await q.get()
                yield event
                if event.event_type == "pipeline_complete":
                    return
        finally:
            self._queues[screening_id].remove(q)
            if not self._queues[screening_id]:
                del self._queues[screening_id]
