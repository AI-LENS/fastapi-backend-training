"""Append-only, hash-chained audit log model.

Each entry's hash is sha256(prev_hash || canonical-JSON-of-entry-fields).
A modified row breaks the chain from that point forward — tamper detection.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    seq: Mapped[int] = mapped_column(
        Integer, autoincrement=True, unique=True, index=True, nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )

    actor_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    actor_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # `metadata` is reserved on DeclarativeBase, so the column is named `event_metadata`
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)
