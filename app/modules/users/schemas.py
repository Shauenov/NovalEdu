from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    avatar_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=255)
    avatar_url: str | None = Field(None, max_length=500)


class StudentListItem(BaseModel):
    id: UUID
    full_name: str
    email: str
    group_type: str | None = None
    course_year: int | None = None
    gpa: float | None = None
    ielts_passed: bool | None = None
    ielts_score: float | None = None
    sat_passed: bool | None = None
    avatar_url: str | None = None
    tasks_total: int = 0
    tasks_done: int = 0
    unread_messages: int = 0

    model_config = {"from_attributes": True}


class StudentDetail(BaseModel):
    user: UserOut
    profile: dict | None = None
    documents: list = []
    active_roadmap: dict | None = None
    tasks_summary: dict = {}
    next_appointment: dict | None = None


class PaginatedMeta(BaseModel):
    page: int
    page_size: int
    total: int


class PaginatedStudents(BaseModel):
    success: bool = True
    data: list[StudentListItem]
    meta: PaginatedMeta


class UserResponse(BaseModel):
    success: bool = True
    data: UserOut


class StudentDetailResponse(BaseModel):
    success: bool = True
    data: StudentDetail
