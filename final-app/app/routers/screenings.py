"""Screening routes — final state (Modules 02→27)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.common import idempotency
from app.db.unit_of_work import UnitOfWork
from app.dependencies import (
    CursorPagination,
    get_cursor_pagination,
    get_current_user,
    get_db_session,
    get_idempotency_key,
    get_progress_manager,
    require_role,
)
from app.dependencies import get_uow
from app.models.user import User
from app.schemas.screening import (
    ScreeningCreate,
    ScreeningListResponse,
    ScreeningResponse,
)
from app.services import screening_service as service
from app.services.progress_manager import ProgressManager

router = APIRouter(
    prefix="/screenings",
    tags=["screenings"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "",
    status_code=201,
    dependencies=[Depends(require_role("coordinator", strict=True))],
)
async def create_screening(
    payload: ScreeningCreate,
    user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
    db: AsyncSession = Depends(get_db_session),
    idem_key: str | None = Depends(get_idempotency_key),
):
    async def _perform():
        screening = await service.submit_screening(uow, user=user, payload=payload)
        return 201, ScreeningResponse.model_validate(screening).model_dump(mode="json")

    if idem_key:
        return await idempotency.get_or_store(
            db, key=idem_key, route="POST /screenings", perform=_perform,
        )
    status, body = await _perform()
    return JSONResponse(status_code=status, content=body)


@router.get("", response_model=ScreeningListResponse)
async def list_screenings(
    site_id: str | None = None,
    status: str | None = None,
    pagination: CursorPagination = Depends(get_cursor_pagination),
    user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    items, next_cursor = await service.list_screenings(
        uow,
        user=user,
        site_id=site_id,
        status=status,
        cursor=pagination.cursor,
        limit=pagination.limit,
    )
    return ScreeningListResponse(
        items=[ScreeningResponse.model_validate(s) for s in items],
        next_cursor=next_cursor,
    )


@router.get("/{screening_id}", response_model=ScreeningResponse)
async def get_screening(
    screening_id: UUID,
    user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    return await service.get_screening(uow, screening_id=screening_id, user=user)


@router.get("/{screening_id}/progress")
async def screening_progress(
    screening_id: UUID,
    request: Request,
    progress: ProgressManager = Depends(get_progress_manager),
    _user: User = Depends(get_current_user),
):
    """SSE stream of pipeline progress."""
    from dataclasses import asdict

    async def event_generator():
        async for event in progress.subscribe(screening_id):
            if await request.is_disconnected():
                break
            yield {"event": event.event_type, "data": asdict(event)}

    return EventSourceResponse(event_generator())


@router.post(
    "/{screening_id}/enroll",
    dependencies=[Depends(require_role("coordinator", strict=True))],
)
async def enroll(
    screening_id: UUID,
    user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
    db: AsyncSession = Depends(get_db_session),
    idem_key: str | None = Depends(get_idempotency_key),
):
    async def _perform():
        screening = await service.enroll_screening(
            uow, screening_id=screening_id, user=user
        )
        return 200, ScreeningResponse.model_validate(screening).model_dump(mode="json")

    if idem_key:
        return await idempotency.get_or_store(
            db,
            key=idem_key,
            route=f"POST /screenings/{screening_id}/enroll",
            perform=_perform,
        )
    status, body = await _perform()
    return JSONResponse(status_code=status, content=body)


@router.delete(
    "/{screening_id}",
    status_code=204,
    dependencies=[Depends(require_role("coordinator", strict=True))],
)
async def delete_screening(
    screening_id: UUID,
    user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    await service.cancel_screening(uow, screening_id=screening_id, user=user)
