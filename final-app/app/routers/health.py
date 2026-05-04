"""Health endpoints for orchestrator probes (Module 26)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session, get_task_runner

router = APIRouter(tags=["ops"])
logger = logging.getLogger(__name__)

_app_ready = False


def set_ready(ready: bool) -> None:
    global _app_ready
    _app_ready = ready


@router.get("/health/live", include_in_schema=False)
async def liveness():
    """Liveness — is the process alive? Cheapest possible check."""
    return {"status": "alive"}


@router.get("/health/ready", include_in_schema=False)
async def readiness(
    db: AsyncSession = Depends(get_db_session),
    runner=Depends(get_task_runner),
):
    """Readiness — can we accept traffic? Verifies DB and worker capacity."""
    if not _app_ready:
        raise HTTPException(503, detail={"status": "starting"})
    try:
        await db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.warning("Readiness DB check failed: %s", exc)
        raise HTTPException(503, detail={"status": "db_unreachable"})
    if runner.active_count() > 100:
        raise HTTPException(
            503,
            detail={"status": "saturated", "active_jobs": runner.active_count()},
        )
    return {"status": "ready", "active_jobs": runner.active_count()}


@router.get("/health/startup", include_in_schema=False)
async def startup_probe():
    if _app_ready:
        return {"status": "ready"}
    raise HTTPException(503, detail={"status": "starting"})


@router.get("/health", include_in_schema=False)
async def simple_health():
    return {"status": "ok"}
