"""Append-only repo for audit logs. Hash-chained for tamper detection.

Module 17c describes this fully. Deliberately exposes no UPDATE/DELETE.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


def _compute_hash(prev_hash: str | None, payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str).encode()
    h = hashlib.sha256()
    if prev_hash:
        h.update(prev_hash.encode())
    h.update(canonical)
    return h.hexdigest()


async def append(
    db: AsyncSession,
    *,
    actor_id: str | None,
    actor_role: str | None,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    metadata = metadata or {}
    occurred_at = datetime.now(timezone.utc)

    last_stmt = select(AuditLog).order_by(desc(AuditLog.seq)).limit(1)
    last = (await db.execute(last_stmt)).scalars().first()
    prev_hash = last.entry_hash if last else None
    next_seq = (last.seq + 1) if last else 1

    # `seq` (integer) replaces `occurred_at` in the hash to avoid SQLite
    # datetime-roundtrip ambiguity. seq is monotonic and roundtrip-stable.
    payload = {
        "seq": next_seq,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "event_metadata": metadata,
    }
    entry_hash = _compute_hash(prev_hash, payload)

    entry = AuditLog(
        seq=next_seq,
        occurred_at=occurred_at,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        event_metadata=metadata,
        prev_hash=prev_hash,
        entry_hash=entry_hash,
    )
    db.add(entry)
    await db.flush()
    return entry


async def list_filtered(
    db: AsyncSession,
    *,
    actor_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    action: str | None = None,
    limit: int = 100,
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(desc(AuditLog.seq)).limit(limit)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    if resource_id:
        stmt = stmt.where(AuditLog.resource_id == resource_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    return list((await db.execute(stmt)).scalars().all())


async def verify_chain(
    db: AsyncSession, *, batch_size: int = 1000
) -> tuple[bool, int | None]:
    """Walk the chain. Returns (ok, broken_seq)."""
    offset = 0
    prev_hash: str | None = None
    while True:
        stmt = (
            select(AuditLog)
            .order_by(AuditLog.seq.asc())
            .offset(offset)
            .limit(batch_size)
        )
        batch = list((await db.execute(stmt)).scalars().all())
        if not batch:
            return True, None
        for entry in batch:
            payload = {
                "seq": entry.seq,
                "actor_id": entry.actor_id,
                "actor_role": entry.actor_role,
                "action": entry.action,
                "resource_type": entry.resource_type,
                "resource_id": entry.resource_id,
                "event_metadata": entry.event_metadata,
            }
            expected = _compute_hash(prev_hash, payload)
            if entry.entry_hash != expected or entry.prev_hash != prev_hash:
                return False, entry.seq
            prev_hash = entry.entry_hash
        offset += batch_size
