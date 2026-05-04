"""Idempotency-key storage helper (Module 27)."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency import IdempotencyKey


async def get_or_store(
    db: AsyncSession,
    *,
    key: str,
    route: str,
    perform: Callable[[], Awaitable[tuple[int, dict]]],
) -> JSONResponse:
    """If `(key, route)` exists, return its stored response. Otherwise execute and store."""
    existing = await db.execute(
        select(IdempotencyKey).where(
            IdempotencyKey.key == key,
            IdempotencyKey.route == route,
        )
    )
    cached = existing.scalars().first()
    if cached is not None:
        return JSONResponse(status_code=cached.response_status, content=cached.response_body)

    status, body = await perform()

    db.add(
        IdempotencyKey(
            key=key,
            route=route,
            response_status=status,
            response_body=body,
        )
    )
    await db.commit()

    return JSONResponse(status_code=status, content=body)
