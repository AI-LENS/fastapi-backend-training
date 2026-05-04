"""Background task runner (Module 13).

Schedules async coroutines as tracked tasks. Concurrency-bounded by semaphore.
Updates the worker_queue_size Prometheus gauge (Module 21).
"""
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Awaitable, Callable
from uuid import UUID

from app.core.metrics import worker_queue_size

logger = logging.getLogger(__name__)


class BackgroundTaskRunner:
    def __init__(self, executor: ThreadPoolExecutor, *, max_concurrency: int = 10):
        self._executor = executor
        self._tasks: dict[UUID, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(max_concurrency)

    @property
    def executor(self) -> ThreadPoolExecutor:
        return self._executor

    def submit(self, key: UUID, coro_factory: Callable[[], Awaitable[None]]) -> None:
        if key in self._tasks and not self._tasks[key].done():
            logger.warning("Task %s already running, ignoring duplicate submit", key)
            return

        async def runner():
            async with self._semaphore:
                try:
                    logger.info("Worker started: %s", key)
                    await coro_factory()
                    logger.info("Worker finished: %s", key)
                except asyncio.CancelledError:
                    logger.info("Worker cancelled: %s", key)
                    raise
                except Exception:
                    logger.exception("Worker failed: %s", key)
                finally:
                    self._update_gauge()

        self._tasks[key] = asyncio.create_task(runner())
        self._update_gauge()

    def _update_gauge(self) -> None:
        worker_queue_size.set(self.active_count())

    def active_count(self) -> int:
        return sum(1 for t in self._tasks.values() if not t.done())

    def cancel(self, key: UUID) -> bool:
        task = self._tasks.get(key)
        if task is None or task.done():
            return False
        task.cancel()
        return True

    async def shutdown(self, timeout: float = 10.0) -> None:
        for task in self._tasks.values():
            if not task.done():
                task.cancel()
        if self._tasks:
            await asyncio.wait(list(self._tasks.values()), timeout=timeout)
        self._executor.shutdown(wait=False)
