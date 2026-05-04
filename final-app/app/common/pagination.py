"""Cursor pagination helpers (Module 27)."""
from __future__ import annotations

import base64
import json
from datetime import datetime
from uuid import UUID


def encode_cursor(created_at: datetime, id_: UUID) -> str:
    payload = {"ts": created_at.isoformat(), "id": str(id_)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    raw = base64.urlsafe_b64decode(cursor.encode())
    data = json.loads(raw)
    return datetime.fromisoformat(data["ts"]), UUID(data["id"])
