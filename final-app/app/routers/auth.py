"""Auth routes (Module 16). Login + refresh + me."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db_session
from app.models.user import User
from app.schemas.auth import (
    AccessTokenOut,
    LoginRequest,
    RefreshRequest,
    TokenPair,
    UserOut,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
_limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=TokenPair)
@_limiter.limit("5/minute")
async def login(
    request: Request,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
):
    access, refresh = await auth_service.login(db, payload.email, payload.password)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=AccessTokenOut)
async def refresh(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db_session),
):
    access = await auth_service.refresh(db, payload.refresh_token)
    return AccessTokenOut(access_token=access)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
