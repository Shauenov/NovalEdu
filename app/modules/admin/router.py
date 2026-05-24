from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, require_admin
from app.core.response import SuccessResponse
from app.database import get_db
from app.modules.admin.schemas import (
    AdminStatsResponse,
    AdminUserResponse,
    CreateAdminUserBody,
    PaginatedAdminAdvisers,
    PaginatedAdminUsers,
    ResetPasswordBody,
    UpdateAdminUserBody,
)
from app.modules.admin.service import AdminService

router = APIRouter()

_admin = Depends(require_admin())


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/admin/stats", response_model=AdminStatsResponse, tags=["Admin"])
async def admin_stats(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = _admin,
) -> AdminStatsResponse:
    service = AdminService(db)
    data = await service.get_stats()
    return AdminStatsResponse(data=data)


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/admin/users", response_model=PaginatedAdminUsers, tags=["Admin"])
async def admin_list_users(
    search: Optional[str] = Query(None, max_length=200),
    role: Optional[str] = Query(None, pattern="^(student|adviser|admin|all)$"),
    status: Optional[str] = Query(None, pattern="^(all|active|inactive)$"),
    sort_by: Optional[str] = Query("created_at", pattern="^(full_name|created_at|role)$"),
    sort_dir: Optional[str] = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = _admin,
) -> PaginatedAdminUsers:
    service = AdminService(db)
    return await service.list_users(
        search=search,
        role=role,
        status=status,
        sort_by=sort_by or "created_at",
        sort_dir=sort_dir or "desc",
        page=page,
        page_size=page_size,
    )


@router.post("/admin/users", response_model=AdminUserResponse, status_code=201, tags=["Admin"])
async def admin_create_user(
    body: CreateAdminUserBody,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = _admin,
) -> AdminUserResponse:
    service = AdminService(db)
    data = await service.create_user(body)
    return AdminUserResponse(data=data)


@router.get("/admin/users/{user_id}", response_model=AdminUserResponse, tags=["Admin"])
async def admin_get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = _admin,
) -> AdminUserResponse:
    service = AdminService(db)
    data = await service.get_user(user_id)
    return AdminUserResponse(data=data)


@router.patch("/admin/users/{user_id}", response_model=AdminUserResponse, tags=["Admin"])
async def admin_update_user(
    user_id: UUID,
    body: UpdateAdminUserBody,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = _admin,
) -> AdminUserResponse:
    service = AdminService(db)
    data = await service.update_user(user_id, body)
    return AdminUserResponse(data=data)


@router.post("/admin/users/{user_id}/reset-password", response_model=SuccessResponse, tags=["Admin"])
async def admin_reset_password(
    user_id: UUID,
    body: ResetPasswordBody,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = _admin,
) -> SuccessResponse:
    service = AdminService(db)
    await service.reset_password(user_id, body.new_password)
    return SuccessResponse()


@router.delete("/admin/users/{user_id}", response_model=SuccessResponse, tags=["Admin"])
async def admin_delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = _admin,
) -> SuccessResponse:
    service = AdminService(db)
    await service.delete_user(user_id, current_user.user_id)
    return SuccessResponse()


# ── Advisers ──────────────────────────────────────────────────────────────────

@router.get("/admin/advisers", response_model=PaginatedAdminAdvisers, tags=["Admin"])
async def admin_list_advisers(
    search: Optional[str] = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = _admin,
) -> PaginatedAdminAdvisers:
    service = AdminService(db)
    return await service.list_advisers(search=search, page=page, page_size=page_size)
