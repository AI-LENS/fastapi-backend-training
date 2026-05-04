"""Business logic for screenings.

Composes UoW (10b) + permission service (18b) + audit (17c) +
outbox (28) + pipeline (14) + progress manager (15).
"""
from __future__ import annotations

from uuid import UUID, uuid4

from app.cache import sites as site_cache
from app.cache import screenings as screening_cache
from app.database import async_session
from app.db.unit_of_work import UnitOfWork
from app.exceptions import (
    AlreadyEnrolled,
    CannotDelete,
    IneligibleScreening,
    InvalidSite,
    ScreeningNotFound,
)
from app.models.screening import Screening
from app.models.user import User
from app.pipelines.eligibility import run_pipeline
from app.repositories import audit_repository as audit
from app.repositories import outbox_repository as outbox
from app.repositories import screening_repository as repo
from app.schemas.screening import ScreeningCreate
from app.services import permission_service
from app.services.progress_manager import ProgressEvent, ProgressManager
from app.workers.task_runner import BackgroundTaskRunner


# ─── User-facing operations (called from routes) ─────────────────────

async def submit_screening(
    uow: UnitOfWork,
    *,
    user: User,
    payload: ScreeningCreate,
) -> Screening:
    """Atomic: validate site, create screening, audit, register outbox event."""
    async with uow:
        await permission_service.ensure_can_submit_for_site(
            uow.session, user, payload.site_id
        )

        site = await site_cache.get_site_cached(uow.session, payload.site_id)
        if site is None or not site.active:
            raise InvalidSite(
                f"Site {payload.site_id} is unknown or inactive",
                details={"site_id": payload.site_id},
            )

        screening = await repo.create(uow.session, **payload.model_dump())

        await audit.append(
            uow.session,
            actor_id=str(user.id),
            actor_role=user.role,
            action="screening.submitted",
            resource_type="screening",
            resource_id=str(screening.id),
            metadata={"site_id": screening.site_id},
        )

        # Reliable publish: outbox row commits with the screening
        await outbox.append(
            uow.session,
            event_type="eligibility.requested",
            payload={"screening_id": str(screening.id)},
        )

        return screening


async def get_screening(
    uow: UnitOfWork,
    *,
    screening_id: UUID,
    user: User,
) -> Screening:
    async with uow:
        screening = await screening_cache.get_screening_cached(
            uow.session, screening_id
        )
        if screening is None:
            raise ScreeningNotFound(f"Screening {screening_id} not found")
        await permission_service.ensure_can_access_screening(
            uow.session, user, screening
        )
        return screening


async def get_screening_summary(uow: UnitOfWork, screening_id: UUID) -> Screening:
    """Minimal view, no object-level check; the response schema redacts fields."""
    async with uow:
        screening = await repo.get_by_id(uow.session, screening_id)
        if screening is None:
            raise ScreeningNotFound(f"Screening {screening_id} not found")
        return screening


async def list_screenings(
    uow: UnitOfWork,
    *,
    user: User,
    site_id: str | None = None,
    status: str | None = None,
    cursor: tuple | None = None,
    limit: int = 50,
) -> tuple[list[Screening], str | None]:
    if user.role == "coordinator":
        site_id = user.site_id
    async with uow:
        return await repo.list_paginated(
            uow.session,
            site_id=site_id,
            status=status,
            cursor=cursor,
            limit=limit,
        )


async def cancel_screening(
    uow: UnitOfWork,
    *,
    screening_id: UUID,
    user: User,
) -> None:
    async with uow:
        screening = await repo.get_by_id(uow.session, screening_id)
        if screening is None:
            raise ScreeningNotFound(f"Screening {screening_id} not found")
        await permission_service.ensure_can_access_screening(
            uow.session, user, screening
        )
        await permission_service.ensure_can_modify_screening(
            uow.session, user, screening, operation="cancel"
        )
        if screening.status != "submitted":
            raise CannotDelete(
                f"Cannot delete screening in status {screening.status}"
            )
        await repo.delete(uow.session, screening)
        screening_cache.invalidate_screening(screening_id)


async def enroll_screening(
    uow: UnitOfWork,
    *,
    screening_id: UUID,
    user: User,
) -> Screening:
    async with uow:
        screening = await repo.get_by_id(uow.session, screening_id)
        if screening is None:
            raise ScreeningNotFound(f"Screening {screening_id} not found")
        await permission_service.ensure_can_access_screening(
            uow.session, user, screening
        )
        await permission_service.ensure_can_modify_screening(
            uow.session, user, screening, operation="enroll"
        )

        if screening.status == "enrolled":
            raise AlreadyEnrolled(
                f"Screening {screening_id} is already enrolled as {screening.subject_id}"
            )
        if screening.eligibility_result != "eligible":
            raise IneligibleScreening(
                f"Screening {screening_id} is not eligible (result: {screening.eligibility_result})"
            )

        subject_id = _generate_subject_id()
        await repo.mark_enrolled(uow.session, screening, subject_id=subject_id)

        await audit.append(
            uow.session,
            actor_id=str(user.id),
            actor_role=user.role,
            action="screening.enrolled",
            resource_type="screening",
            resource_id=str(screening_id),
            metadata={"subject_id": subject_id, "site_id": screening.site_id},
        )

        screening_cache.invalidate_screening(screening_id)
        return screening


def _generate_subject_id() -> str:
    return "S-" + uuid4().hex[:8].upper()


# ─── Worker-side dispatch (called by outbox drainer) ───────────────────

def dispatch_eligibility_pipeline(
    runner: BackgroundTaskRunner,
    progress: ProgressManager,
    screening_id: UUID,
) -> None:
    """Schedule the eligibility pipeline as a background task."""

    async def _job():
        async with async_session() as db:
            screening = await repo.get_by_id(db, screening_id)
            if not screening or screening.status != "submitted":
                return

            await repo.update_status(db, screening, status="reviewing")
            await db.commit()
            screening_cache.invalidate_screening(screening_id)

            await progress.emit(
                screening_id,
                ProgressEvent(event_type="started", screening_id=str(screening_id)),
            )

            async def on_stage(result):
                await progress.emit(
                    screening_id,
                    ProgressEvent(
                        event_type="stage_complete",
                        screening_id=str(screening_id),
                        stage=result.name,
                        passed=result.passed,
                        reason=result.reason,
                    ),
                )

            outcome = await run_pipeline(screening, on_stage_complete=on_stage)

            await repo.update_status(
                db,
                screening,
                status="eligible" if outcome.eligible else "ineligible",
                eligibility_result="eligible" if outcome.eligible else "ineligible",
                failed_criteria=outcome.failed_criteria,
            )
            await db.commit()
            screening_cache.invalidate_screening(screening_id)

            await progress.emit(
                screening_id,
                ProgressEvent(
                    event_type="pipeline_complete",
                    screening_id=str(screening_id),
                    eligible=outcome.eligible,
                    failed_criteria=outcome.failed_criteria,
                ),
            )

    runner.submit(screening_id, _job)
