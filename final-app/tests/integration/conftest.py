"""Integration test fixtures (Module 23).

Each test gets:
  - A fresh in-memory SQLite DB (tables created from models)
  - A fresh FastAPI app (no lifespan, deps overridden)
  - A pre-seeded set of users and sites
  - An async HTTPX client
"""
from __future__ import annotations

from typing import AsyncIterator

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.cache import screenings as screening_cache
from app.cache import sites as site_cache
from app.db.unit_of_work import UnitOfWork
from app.dependencies import get_db_session, get_progress_manager, get_task_runner, get_uow
from app.exceptions import DomainError
from app.middleware.metrics import MetricsMiddleware
from app.middleware.request_id import RequestIDMiddleware, get_request_id
from app.models.base import Base
from app.models.site import Site
from app.models.user import User
from app.repositories import site_repository, user_repository
from app.routers import admin, auth, health, screenings, sites
from app.services.auth_service import hash_password
from app.services.progress_manager import ProgressManager
from app.workers.task_runner import BackgroundTaskRunner

from concurrent.futures import ThreadPoolExecutor
from fastapi.responses import JSONResponse


@pytest_asyncio.fixture
async def engine():
    # StaticPool: every session shares the same connection — required so the
    # dispatcher's session sees rows written by the request's session
    # (in-memory SQLite is per-connection).
    from sqlalchemy.pool import StaticPool
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Clear in-memory caches between tests
    site_cache.clear()
    screening_cache.clear()
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def seeded(session_factory) -> dict:
    async with session_factory() as db:
        await site_repository.seed(
            db,
            [
                Site(id="SITE-001", name="Site 001", active=True),
                Site(id="SITE-002", name="Site 002", active=True),
            ],
        )
        sponsor = User(
            email="admin@test.com",
            hashed_password=hash_password("pwd"),
            full_name="Admin",
            role="sponsor",
        )
        alice = User(
            email="alice@test.com",
            hashed_password=hash_password("pwd"),
            full_name="Alice",
            role="coordinator",
            site_id="SITE-001",
        )
        bob = User(
            email="bob@test.com",
            hashed_password=hash_password("pwd"),
            full_name="Bob",
            role="coordinator",
            site_id="SITE-002",
        )
        for u in [sponsor, alice, bob]:
            db.add(u)
        await db.commit()
    return {"sponsor_email": sponsor.email, "alice_email": alice.email, "bob_email": bob.email}


def _build_test_app(session_factory):
    """Build a test app without the production lifespan (which would re-create_all)."""
    app = FastAPI(title="Test Subject Enrollment Service")

    # Same middleware stack the production app uses
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # Same exception handler
    @app.exception_handler(DomainError)
    async def handle_domain(request, exc: DomainError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": get_request_id(),
                }
            },
        )

    # Test-only worker + progress (real ones, no lifespan)
    executor = ThreadPoolExecutor(max_workers=2)
    app.state.executor = executor
    app.state.task_runner = BackgroundTaskRunner(executor=executor, max_concurrency=4)
    app.state.progress = ProgressManager()

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(sites.router, prefix="/api/v1")
    app.include_router(screenings.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    return app


@pytest_asyncio.fixture
async def app(session_factory, seeded) -> AsyncIterator[FastAPI]:
    # Reset slowapi rate limiter state so login limits don't leak between tests
    from app.routers.auth import _limiter
    _limiter.reset()

    # The dispatcher opens its own session via the production-global
    # `async_session` factory. In tests we redirect it to our in-memory factory.
    from app.services import screening_service as _svc
    _orig_async_session = _svc.async_session
    _svc.async_session = session_factory

    test_app = _build_test_app(session_factory)

    async def _override_db():
        async with session_factory() as session:
            yield session

    def _override_uow():
        return UnitOfWork(session_factory)

    test_app.dependency_overrides[get_db_session] = _override_db
    test_app.dependency_overrides[get_uow] = _override_uow
    test_app.dependency_overrides[get_task_runner] = lambda: test_app.state.task_runner
    test_app.dependency_overrides[get_progress_manager] = lambda: test_app.state.progress

    # Mark the app as ready for the readiness probe
    from app.routers.health import set_ready
    set_ready(True)

    yield test_app

    test_app.dependency_overrides.clear()
    await test_app.state.task_runner.shutdown(timeout=2.0)

    # Restore the real async_session
    _svc.async_session = _orig_async_session


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


@pytest_asyncio.fixture
async def alice_token(client) -> str:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@test.com", "password": "pwd"},
    )
    return r.json()["access_token"]


@pytest_asyncio.fixture
async def alice_auth(alice_token):
    return {"Authorization": f"Bearer {alice_token}"}


@pytest_asyncio.fixture
async def bob_token(client) -> str:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "bob@test.com", "password": "pwd"},
    )
    return r.json()["access_token"]


@pytest_asyncio.fixture
async def bob_auth(bob_token):
    return {"Authorization": f"Bearer {bob_token}"}


@pytest_asyncio.fixture
async def admin_token(client) -> str:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "pwd"},
    )
    return r.json()["access_token"]


@pytest_asyncio.fixture
async def admin_auth(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
