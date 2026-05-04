"""Audit log schema."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    occurred_at: datetime
    actor_id: str | None
    actor_role: str | None
    action: str
    resource_type: str
    resource_id: str
    event_metadata: dict = Field(default_factory=dict)
