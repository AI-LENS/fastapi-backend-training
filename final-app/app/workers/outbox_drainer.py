"""Outbox drainer (Module 28).

Periodically reads unpublished outbox events and dispatches them.
For training, we dispatch in-process to the BackgroundTaskRunner. In a
multi-process setup, dispatch would enqueue to Arq/Celery instead.
"""
from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from app.database import async_session
from app.repositories import outbox_repository as outbox

logger = logging.getLogger(__name__)


async def drain_loop(
    runner,
    progress,
    *,
    interval_s: float = 1.0,
) -> None:
    """Run forever (until cancelled). Picks up unpublished events and dispatches."""
    # Local import avoids circular dependency
    from app.services.screening_service import dispatch_eligibility_pipeline

    while True:
        try:
            async with async_session() as db:
                events = await outbox.fetch_unpublished(db, limit=100)
                for event in events:
                    if event.event_type == "eligibility.requested":
                        screening_id = UUID(event.payload["screening_id"])
                        dispatch_eligibility_pipeline(runner, progress, screening_id)
                    await outbox.mark_published(db, event.id)
                if events:
                    await db.commit()
                    logger.info("Drained %d outbox events", len(events))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Outbox drainer error")
        try:
            await asyncio.sleep(interval_s)
        except asyncio.CancelledError:
            raise
