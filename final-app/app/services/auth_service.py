"""JWT auth service (Module 16). Login, hashing, token issue/verify."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import InvalidCredentials
from app.models.user import User
from app.repositories import user_repository as user_repo


_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plaintext: str) -> str:
    return _pwd_ctx.hash(plaintext)


def verify_password(plaintext: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plaintext, hashed)


def _encode(claims: dict[str, Any]) -> str:
    return jwt.encode(claims, settings.secret_key, algorithm="HS256")


def issue_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    return _encode({
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "site_id": user.site_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    })


def issue_refresh_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    return _encode({
        "sub": str(user.id),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_days),
    })


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise InvalidCredentials("Invalid or expired token") from exc


async def login(db: AsyncSession, email: str, password: str) -> tuple[str, str]:
    user = await user_repo.get_by_email(db, email)
    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        raise InvalidCredentials("Invalid email or password")
    return issue_access_token(user), issue_refresh_token(user)


async def refresh(db: AsyncSession, refresh_token: str) -> str:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise InvalidCredentials("Wrong token type")
    user = await user_repo.get_by_id(db, payload["sub"])
    if user is None or not user.is_active:
        raise InvalidCredentials("User not found or disabled")
    return issue_access_token(user)
