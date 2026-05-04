"""Database access for Users."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def get_by_id(db: AsyncSession, user_id: UUID | str) -> User | None:
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    return await db.get(User, user_id)


async def create(db: AsyncSession, user: User) -> User:
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def list_all(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User))
    return list(result.scalars().all())
