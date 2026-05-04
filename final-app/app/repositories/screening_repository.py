"""Database access for the Screening resource. The ONLY place we write SQL for screenings.

Following the UoW pattern (Module 10b): repos `flush()` but never `commit()` —
service-level UnitOfWork commits when the unit of work is done.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.screening import Screening


async def create(db: AsyncSession, **fields) -> Screening:
    screening = Screening(**fields)
    db.add(screening)
    await db.flush()
    await db.refresh(screening)
    return screening


async def get_by_id(db: AsyncSession, screening_id: UUID) -> Screening | None:
    return await db.get(Screening, screening_id)


async def list_filtered(
    db: AsyncSession,
    *,
    site_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[Screening]:
    stmt = select(Screening).order_by(Screening.created_at.desc()).limit(limit)
    if site_id is not None:
        stmt = stmt.where(Screening.site_id == site_id)
    if status is not None:
        stmt = stmt.where(Screening.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_paginated(
    db: AsyncSession,
    *,
    site_id: str | None = None,
    status: str | None = None,
    cursor: tuple[datetime, UUID] | None = None,
    limit: int = 50,
) -> tuple[list[Screening], str | None]:
    """Returns (items, next_cursor). next_cursor=None when no more pages."""
    from app.common.pagination import encode_cursor

    stmt = (
        select(Screening)
        .order_by(Screening.created_at.desc(), Screening.id.desc())
        .limit(limit + 1)
    )
    if site_id is not None:
        stmt = stmt.where(Screening.site_id == site_id)
    if status is not None:
        stmt = stmt.where(Screening.status == status)
    if cursor is not None:
        cursor_ts, cursor_id = cursor
        stmt = stmt.where(
            (Screening.created_at < cursor_ts)
            | ((Screening.created_at == cursor_ts) & (Screening.id < cursor_id))
        )

    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    if len(rows) > limit:
        last = rows[limit - 1]
        next_cursor = encode_cursor(last.created_at, last.id)
        rows = rows[:limit]
    else:
        next_cursor = None
    return rows, next_cursor


async def update_status(
    db: AsyncSession,
    screening: Screening,
    *,
    status: str,
    eligibility_result: str | None = None,
    failed_criteria: list[str] | None = None,
) -> Screening:
    screening.status = status
    if eligibility_result is not None:
        screening.eligibility_result = eligibility_result
    if failed_criteria is not None:
        screening.failed_criteria = failed_criteria
    await db.flush()
    return screening


async def mark_enrolled(
    db: AsyncSession,
    screening: Screening,
    *,
    subject_id: str,
) -> Screening:
    screening.status = "enrolled"
    screening.subject_id = subject_id
    screening.enrolled_at = datetime.now(timezone.utc)
    await db.flush()
    return screening


async def delete(db: AsyncSession, screening: Screening) -> None:
    await db.delete(screening)
    await db.flush()
