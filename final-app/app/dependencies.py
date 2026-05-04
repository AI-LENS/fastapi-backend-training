"""Dependency providers for the application (Modules 10, 13, 15, 16, 17, 27)."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import decode_cursor
from app.database import async_session
from app.db.unit_of_work import UnitOfWork
from app.exceptions import Forbidden, Unauthorized
from app.models.user import User
from app.repositories import user_repository as user_repo
from app.services import auth_service


_bearer = HTTPBearer(auto_error=False)


# ─── Database / UoW ─────────────────────────────────────────

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


def get_uow() -> UnitOfWork:
    return UnitOfWork(async_session)


# ─── App-state injectors (typed wrappers around request.app.state) ──

def get_task_runner(request: Request):
    return request.app.state.task_runner


def get_progress_manager(request: Request):
    return request.app.state.progress


# ─── Auth ───────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    if credentials is None:
        raise Unauthorized("Missing bearer token")
    payload = auth_service.decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise Unauthorized("Wrong token type")
    user = await user_repo.get_by_id(db, payload["sub"])
    if user is None or not user.is_active:
        raise Unauthorized("User not found or disabled")
    structlog.contextvars.bind_contextvars(
        user_id=str(user.id),
        user_role=user.role,
        site_id=user.site_id,
    )
    return user


def require_role(*allowed_roles: str, strict: bool = False):
    """Return a dep that requires at least one of the given roles.

    By default sponsors are auto-allowed (admin override). Pass strict=True
    to disable that override (action is for a specific role only).
    """

    async def _check(user: User = Depends(get_current_user)) -> User:
        if not strict and user.role == "sponsor":
            return user
        if user.role not in allowed_roles:
            raise Forbidden(
                f"Role {user.role!r} not allowed; required: {list(allowed_roles)}",
                details={"required_roles": list(allowed_roles)},
            )
        return user

    return _check


# ─── Pagination ─────────────────────────────────────────────

@dataclass
class CursorPagination:
    cursor: tuple[datetime, UUID] | None
    limit: int


def get_cursor_pagination(
    cursor: str | None = None,
    limit: int = 50,
) -> CursorPagination:
    decoded = decode_cursor(cursor) if cursor else None
    return CursorPagination(cursor=decoded, limit=min(max(limit, 1), 100))


# ─── Idempotency ────────────────────────────────────────────

def get_idempotency_key(
    idempotency_key: Annotated[str | None, Header()] = None,
) -> str | None:
    return idempotency_key
