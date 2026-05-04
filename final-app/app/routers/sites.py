"""Site routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db_session
from app.exceptions import SiteNotFound
from app.models.user import User
from app.repositories import site_repository as repo
from app.schemas.site import SiteResponse

router = APIRouter(
    prefix="/sites",
    tags=["sites"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[SiteResponse])
async def list_sites(
    active: bool | None = None,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
):
    return await repo.list_all(db, active=active)


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: str,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
):
    site = await repo.get_by_id(db, site_id)
    if site is None:
        raise SiteNotFound(
            f"Site {site_id} not found",
            details={"site_id": site_id},
        )
    return site
