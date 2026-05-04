"""Outbox repo: append on commit; mark_published from drainer."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxEvent


async def append(
    db: AsyncSession,
    *,
    event_type: str,
    payload: dict,
) -> OutboxEvent:
    event = OutboxEvent(event_type=event_type, payload=payload)
    db.add(event)
    await db.flush()
    return event


async def fetch_unpublished(
    db: AsyncSession, *, limit: int = 100
) -> list[OutboxEvent]:
    result = await db.execute(
        select(OutboxEvent)
        .where(OutboxEvent.published_at.is_(None))
        .order_by(OutboxEvent.created_at)
        .limit(limit)
    )
    return list(result.scalars().all())


async def mark_published(db: AsyncSession, event_id: UUID) -> None:
    await db.execute(
        update(OutboxEvent)
        .where(OutboxEvent.id == event_id)
        .values(published_at=datetime.now(timezone.utc))
    )
