"""In-memory site cache (Module 19).

For multi-worker deploys, swap `TTLCache` for a Redis-backed wrapper.
"""
from __future__ import annotations

from cachetools import TTLCache
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.site import Site
from app.repositories import site_repository

_site_cache: TTLCache = TTLCache(maxsize=1000, ttl=60)


async def get_site_cached(db: AsyncSession, site_id: str) -> Site | None:
    cached = _site_cache.get(site_id)
    if cached is not None:
        return cached
    site = await site_repository.get_by_id(db, site_id)
    if site is not None:
        _site_cache[site_id] = site
    return site


def invalidate_site(site_id: str) -> None:
    _site_cache.pop(site_id, None)


def clear() -> None:
    """Clear the entire cache. Used in tests."""
    _site_cache.clear()
