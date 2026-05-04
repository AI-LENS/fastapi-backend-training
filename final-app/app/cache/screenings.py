"""In-memory screening cache (Module 19 exercise)."""
from __future__ import annotations

from uuid import UUID

from cachetools import TTLCache
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.screening import Screening
from app.repositories import screening_repository

_cache: TTLCache = TTLCache(maxsize=10_000, ttl=5)


async def get_screening_cached(db: AsyncSession, screening_id: UUID) -> Screening | None:
    cached = _cache.get(screening_id)
    if cached is not None:
        return cached
    screening = await screening_repository.get_by_id(db, screening_id)
    if screening is not None:
        _cache[screening_id] = screening
    return screening


def invalidate_screening(screening_id: UUID) -> None:
    _cache.pop(screening_id, None)


def clear() -> None:
    _cache.clear()
