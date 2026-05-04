"""Centralized object-level permission service (Module 17b + 18b).

Every object-level access check goes through here. The service:
  1. Decides allow/deny based on policy
  2. Records audit entries for denials (in the same transaction)
  3. Raises a NotFound-style exception (no info leak)

For a single audit-source-of-truth, callers pass the active session — same
transaction as the business write.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import Forbidden, ScreeningNotFound
from app.models.screening import Screening
from app.models.user import User
from app.repositories import audit_repository as audit


# ─── Pure policy functions (testable in isolation) ──────────────────

def _can_access_screening(user: User, screening: Screening) -> bool:
    if user.role == "sponsor":
        return True
    if user.role == "coordinator" and user.site_id == screening.site_id:
        return True
    return False


def _can_modify_screening(user: User, screening: Screening) -> bool:
    if user.role == "coordinator" and user.site_id == screening.site_id:
        return True
    return False


def _can_view_audit_log(user: User) -> bool:
    return user.role == "sponsor"


# ─── Public API: ensure_* methods raise on denial ───────────────────

async def ensure_can_access_screening(
    db: AsyncSession,
    user: User,
    screening: Screening,
) -> None:
    if _can_access_screening(user, screening):
        return
    await audit.append(
        db,
        actor_id=str(user.id),
        actor_role=user.role,
        action="screening.access_denied",
        resource_type="screening",
        resource_id=str(screening.id),
        metadata={
            "user_site": user.site_id,
            "screening_site": screening.site_id,
        },
    )
    raise ScreeningNotFound(f"Screening {screening.id} not found")


async def ensure_can_modify_screening(
    db: AsyncSession,
    user: User,
    screening: Screening,
    *,
    operation: str,
) -> None:
    if _can_modify_screening(user, screening):
        return
    await audit.append(
        db,
        actor_id=str(user.id),
        actor_role=user.role,
        action="screening.modify_denied",
        resource_type="screening",
        resource_id=str(screening.id),
        metadata={
            "operation": operation,
            "user_site": user.site_id,
            "screening_site": screening.site_id,
        },
    )
    raise Forbidden("You cannot modify this screening")


async def ensure_can_submit_for_site(
    db: AsyncSession,
    user: User,
    site_id: str,
) -> None:
    if user.role == "sponsor":
        return
    if user.role == "coordinator" and user.site_id == site_id:
        return
    await audit.append(
        db,
        actor_id=str(user.id),
        actor_role=user.role,
        action="screening.submit_denied",
        resource_type="site",
        resource_id=site_id,
        metadata={"user_site": user.site_id},
    )
    raise Forbidden(
        f"Coordinators may only submit for their own site (yours: {user.site_id})"
    )


async def ensure_can_view_audit_log(db: AsyncSession, user: User) -> None:
    if _can_view_audit_log(user):
        return
    await audit.append(
        db,
        actor_id=str(user.id),
        actor_role=user.role,
        action="audit.view_denied",
        resource_type="audit_log",
        resource_id="all",
        metadata={"user_site": user.site_id},
    )
    raise Forbidden("Only sponsors can view the audit log")
