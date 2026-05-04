"""Admin routes — DLQ, audit log query (Modules 13b + 17c)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db_session, require_role
from app.models.user import User
from app.repositories import audit_repository as audit
from app.repositories import job_record_repository as job_repo
from app.schemas.audit import AuditLogOut
from app.services import permission_service

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_role("sponsor"))],
)


@router.get("/jobs")
async def list_jobs(
    status: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
):
    rows = await job_repo.list_filtered(db, status=status, limit=limit)
    return [
        {
            "id": str(r.id),
            "job_type": r.job_type,
            "target_id": r.target_id,
            "status": r.status,
            "attempts": r.attempts,
            "max_attempts": r.max_attempts,
            "last_error": r.last_error,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }
        for r in rows
    ]


@router.get("/audit", response_model=list[AuditLogOut])
async def list_audit(
    actor_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    action: str | None = None,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    await permission_service.ensure_can_view_audit_log(db, user)
    await db.commit()
    rows = await audit.list_filtered(
        db,
        actor_id=actor_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        limit=limit,
    )
    return rows


@router.post("/audit/verify")
async def verify_audit_chain(db: AsyncSession = Depends(get_db_session)):
    ok, broken_seq = await audit.verify_chain(db)
    return {"chain_intact": ok, "broken_at_seq": broken_seq}
