"""Subject Enrollment Service — entry point.

Final state composing every module's pattern:
  - Layered architecture (routers → services → repos → models)
  - Async SQLAlchemy with create_all on startup (Alembic teaches the prod path)
  - Lifespan with startup/shutdown
  - Multi-middleware stack (CORS, RequestID, AccessLog, Slow, Metrics)
  - Structured logging
  - JWT auth + RBAC + object-level auth + audit log + permission service
  - Background worker + outbox drainer + SSE
  - Custom exception handlers with envelope + request_id
  - Prometheus metrics + readiness/liveness/startup probes
"""
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.metrics import domain_errors_total
from app.database import async_session, close_db, engine
from app.exceptions import DomainError
from app.middleware.logging import AccessLogMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.middleware.request_id import RequestIDMiddleware, get_request_id
from app.middleware.slow import SlowRequestMiddleware
from app.models import Base
from app.models.site import Site
from app.models.user import User
from app.repositories import site_repository, user_repository
from app.routers import admin, auth, health, metrics as metrics_router, screenings, sites
from app.routers.health import set_ready
from app.services.auth_service import hash_password
from app.services.progress_manager import ProgressManager
from app.workers.outbox_drainer import drain_loop
from app.workers.task_runner import BackgroundTaskRunner


configure_logging()
logger = get_logger(__name__)


DEFAULT_SITES = [
    Site(id="SITE-001", name="Mass General", active=True),
    Site(id="SITE-002", name="Stanford Health", active=True),
    Site(id="SITE-003", name="Old Site", active=False),
]


def _default_users() -> list[User]:
    return [
        User(
            email="admin@example.com",
            hashed_password=hash_password("admin"),
            full_name="Default Sponsor",
            role="sponsor",
            site_id=None,
        ),
        User(
            email="alice@example.com",
            hashed_password=hash_password("alice"),
            full_name="Alice (Coordinator @ SITE-001)",
            role="coordinator",
            site_id="SITE-001",
        ),
        User(
            email="bob@example.com",
            hashed_password=hash_password("bob"),
            full_name="Bob (Coordinator @ SITE-002)",
            role="coordinator",
            site_id="SITE-002",
        ),
    ]


async def _seed_sites() -> None:
    async with async_session() as db:
        inserted = await site_repository.seed(db, DEFAULT_SITES)
        if inserted:
            logger.info("seeded sites count=%s", inserted)


async def _seed_users() -> None:
    async with async_session() as db:
        existing = await user_repository.list_all(db)
        if not existing:
            for u in _default_users():
                db.add(u)
            await db.commit()
            logger.info("seeded users: %s", ["admin@example.com", "alice@example.com", "bob@example.com"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup: %s", settings.safe_dump())

    # For training simplicity we use create_all on startup.
    # Module 07 teaches Alembic, the production-grade migration tool.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _seed_sites()
    await _seed_users()

    # Background worker + progress manager
    executor = ThreadPoolExecutor(max_workers=4)
    app.state.executor = executor
    app.state.task_runner = BackgroundTaskRunner(executor=executor, max_concurrency=10)
    app.state.progress = ProgressManager()

    # Outbox drainer — picks up "eligibility.requested" events and dispatches
    drainer_task = asyncio.create_task(
        drain_loop(app.state.task_runner, app.state.progress, interval_s=0.5)
    )
    app.state.drainer_task = drainer_task

    set_ready(True)
    logger.info("ready")
    yield

    # Shutdown
    set_ready(False)
    logger.info("shutting_down")
    drainer_task.cancel()
    try:
        await drainer_task
    except (asyncio.CancelledError, Exception):
        pass
    await app.state.task_runner.shutdown(timeout=15.0)
    await close_db()
    logger.info("shutdown_complete")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError):
        domain_errors_total.labels(code=exc.code).inc()
        logger.info(
            "domain_error method=%s path=%s code=%s message=%s",
            request.method, request.url.path, exc.code, exc.message,
        )
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

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        # Don't shadow domain errors (already handled above)
        if isinstance(exc, DomainError):
            return await handle_domain_error(request, exc)
        domain_errors_total.labels(code="internal_error").inc()
        logging.getLogger(__name__).exception(
            "Unhandled exception on %s %s", request.method, request.url.path
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Internal server error",
                    "request_id": get_request_id(),
                }
            },
        )


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    # Rate limit handler (slowapi)
    app.state.limiter = _rate_limit_exceeded_handler  # placeholder; real Limiter on the router
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Middleware (outermost added first; runs request-side top-to-bottom)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(SlowRequestMiddleware)
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIDMiddleware)

    register_exception_handlers(app)

    # Public routes (no auth)
    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(metrics_router.router)
    app.include_router(auth.router, prefix=settings.api_prefix)

    # Authenticated routes
    app.include_router(sites.router, prefix=settings.api_prefix)
    app.include_router(screenings.router, prefix=settings.api_prefix)
    app.include_router(admin.router, prefix=settings.api_prefix)

    @app.get("/")
    async def root():
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": settings.api_prefix + "/health/live",
        }

    return app


app = create_app()
