"""Database access for Sites."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.site import Site


async def list_all(db: AsyncSession, *, active: bool | None = None) -> list[Site]:
    stmt = select(Site).order_by(Site.id)
    if active is not None:
        stmt = stmt.where(Site.active == active)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, site_id: str) -> Site | None:
    return await db.get(Site, site_id)


async def seed(db: AsyncSession, sites: list[Site]) -> int:
    """Insert sites if the table is empty. Returns count inserted."""
    result = await db.execute(select(Site).limit(1))
    if result.scalars().first() is not None:
        return 0
    db.add_all(sites)
    await db.commit()
    return len(sites)
