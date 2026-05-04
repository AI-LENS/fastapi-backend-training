"""Database access for JobRecord (durable background-job state)."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_record import JobRecord


async def get_or_create(
    db: AsyncSession,
    *,
    idempotency_key: str,
    **fields,
) -> tuple[JobRecord, bool]:
    """Return (record, created) for the given idempotency key."""
    result = await db.execute(
        select(JobRecord).where(JobRecord.idempotency_key == idempotency_key)
    )
    existing = result.scalars().first()
    if existing:
        return existing, False
    record = JobRecord(idempotency_key=idempotency_key, **fields)
    db.add(record)
    await db.flush()
    return record, True


async def get_by_id(db: AsyncSession, job_id: UUID) -> JobRecord | None:
    return await db.get(JobRecord, job_id)


async def list_filtered(
    db: AsyncSession,
    *,
    status: str | None = None,
    limit: int = 50,
) -> list[JobRecord]:
    stmt = select(JobRecord).order_by(desc(JobRecord.updated_at)).limit(limit)
    if status:
        stmt = stmt.where(JobRecord.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def mark_running(db: AsyncSession, record: JobRecord) -> None:
    record.status = "running"
    record.attempts += 1
    await db.flush()


async def mark_succeeded(db: AsyncSession, record: JobRecord) -> None:
    record.status = "succeeded"
    record.last_error = None
    await db.flush()


async def mark_retrying(
    db: AsyncSession,
    record: JobRecord,
    *,
    error: str,
    next_retry_at: datetime,
) -> None:
    record.status = "queued"
    record.last_error = error
    record.last_error_at = datetime.now(timezone.utc)
    record.next_retry_at = next_retry_at
    await db.flush()


async def mark_dead_letter(
    db: AsyncSession,
    record: JobRecord,
    *,
    error: str,
) -> None:
    record.status = "dead_letter"
    record.last_error = error
    record.last_error_at = datetime.now(timezone.utc)
    await db.flush()


async def reset_for_retry(db: AsyncSession, record: JobRecord) -> None:
    record.status = "queued"
    record.attempts = 0
    record.last_error = None
    record.last_error_at = None
    record.next_retry_at = None
    await db.flush()
