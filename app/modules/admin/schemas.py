from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Shared pagination ─────────────────────────────────────────────────────────

class PaginatedMeta(BaseModel):
    page: int
    page_size: int
    total: int


# ── Admin user ────────────────────────────────────────────────────────────────

class AdminUserOut(BaseModel):
    """Full user record visible only to admins."""
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    avatar_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedAdminUsers(BaseModel):
    success: bool = True
    data: list[AdminUserOut]
    meta: PaginatedMeta


class AdminUserResponse(BaseModel):
    success: bool = True
    data: AdminUserOut


class CreateAdminUserBody(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    role: str = Field("student", pattern="^(student|adviser|admin)$")
    password: str = Field(..., min_length=8)


class UpdateAdminUserBody(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=255)
    email: EmailStr | None = None
    role: str | None = Field(None, pattern="^(student|adviser|admin)$")
    is_active: bool | None = None


class ResetPasswordBody(BaseModel):
    new_password: str = Field(..., min_length=8)


# ── Admin stats ───────────────────────────────────────────────────────────────

class RoleBreakdown(BaseModel):
    student: int = 0
    adviser: int = 0
    admin: int = 0


class GrowthPoint(BaseModel):
    month: str          # "Jan", "Feb", ...
    users: int


class AdminStatsOut(BaseModel):
    total_users: int
    by_role: RoleBreakdown
    active_users: int
    inactive_users: int
    growth: list[GrowthPoint] = []


class AdminStatsResponse(BaseModel):
    success: bool = True
    data: AdminStatsOut


# ── Admin advisers ────────────────────────────────────────────────────────────

class AdminAdviserOut(BaseModel):
    user_id: UUID
    full_name: str
    email: str
    avatar_url: str | None = None
    is_active: bool
    created_at: datetime
    headline: str | None = None
    students_placed: int | None = None
    rating_avg: float = 0.0
    reviews_count: int = 0

    model_config = {"from_attributes": True}


class PaginatedAdminAdvisers(BaseModel):
    success: bool = True
    data: list[AdminAdviserOut]
    meta: PaginatedMeta
