"""Async SQLAlchemy engine, session factory, and shutdown helper."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings


engine = create_async_engine(
    settings.db_url,
    echo=False,
    pool_pre_ping=True,
)

async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def close_db() -> None:
    """Dispose engine on shutdown."""
    await engine.dispose()
